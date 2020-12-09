# encoding: utf-8

#import setuptools # for bdist_egg and console_scripts entry point
from setuptools import setup,Extension
#import distutils.command.install_scripts
#import distutils.command.sdist
#import distutils.command.build_ext
import distutils.spawn  # for find_executable
import os.path, os, shutil, re, subprocess, sys, codecs
from glob import glob
from os.path import sep,join,basename,dirname
import logging
logging.basicConfig(level=logging.INFO)
log=logging.getLogger('woo/setup.py')

DISTBUILD=None # set to None if building locally, or to a string when dist-building on a bot
if 'DEB_BUILD_ARCH' in os.environ: DISTBUILD='debian'
WIN=(sys.platform=='win32')
PY3=(sys.version_info[0]==3)
QT5=None # True (qt5), False (qt4), None (qt4/5 not found)
try:
    import PyQt5
    log.info("PyQt5 found.")
    QT5=True
    # needed for good default for QT5 base directory
    multiarchTriplet=getattr(sys,'implementation',sys)._multiarch
    QT5DIR='/usr/lib/'+multiarchTriplet+'/qt5'
    QT5INC='/usr/include/'+multiarchTriplet+'/qt5'
except ImportError:
    log.info('PyQt5 not importable:',exc_info=True)
    if 'WOO_QT5' in os.environ: raise ValueError('WOO_QT5 was specified, but PyQt5 not importable.')
# if we force qt5, don't try to look for qt4 at all
if 'WOO_QT5' not in os.environ:
    try:
        import PyQt4
        log.info("PyQt4 found.")
        if QT5: log.warn('Both PyQt4 and PyQt5 are importable, using QT5.')
        QT5=True
    except ImportError:
        log.info('PyQt4 not importable:',exc_info=True)

travis=False
if 'WOO_FLAVOR' in os.environ:
    f=os.environ['WOO_FLAVOR']
    if f=='travis': travis=True
    else: raise ValueError("Unknown value '%s' for the environment variable WOO_FLAVOR. Recognized values are: travis.")

if not DISTBUILD: # don't do parallel at buildbot
    # monkey-patch for parallel compilation
    def parallelCCompile(self, sources, output_dir=None, macros=None, include_dirs=None, debug=0, extra_preargs=None, extra_postargs=None, depends=None):
        # those lines are copied from distutils.ccompiler.CCompiler directly
        macros, objects, extra_postargs, pp_opts, build = self._setup_compile(output_dir, macros, include_dirs, sources, depends, extra_postargs)
        cc_args = self._get_cc_args(pp_opts, debug, extra_preargs)
        # parallel code
        N=4 # number of parallel compilations by default
        import multiprocessing.pool
        def _single_compile(obj):
            try: src, ext = build[obj]
            except KeyError: return
            print(obj)
            self._compile(obj, src, ext, cc_args, extra_postargs, pp_opts)
        # convert to list, imap is evaluated on-demand
        list(multiprocessing.pool.ThreadPool(N).imap(_single_compile,objects))
        return objects
    import distutils.ccompiler
    distutils.ccompiler.CCompiler.compile=parallelCCompile

pathSourceTree=join('build-src-tree')
pathSources=join(pathSourceTree,'src')
pathScripts=join(pathSourceTree,'scripts')
pathHeaders=join(pathSourceTree,'woo')

## get version info
version=None
revno=None
# on debian, get version from changelog
if DISTBUILD=='debian':
    version=re.match(r'^[^(]* \(([^)]+)\).*$',codecs.open('debian/changelog','r','utf-8').readlines()[0]).group(1)
    log.info('Debian version from changelog: '+str(version))
    revno='debian'
# get version from queryling local bzr repo
if not version:
    revno='na'
    if os.path.exists('.git'):
        try:
            r0=os.popen("git rev-list HEAD --count 2>"+("NUL" if WIN else "/dev/null")).readlines()[0][:-1]
            r1=os.popen("git log -1 --format='%h'").readlines()[0][:-1]
            revno=r0+'+git.'+r1
        except: pass
    elif os.path.exists('.bzr'):
        try:
            # http://stackoverflow.com/questions/3630893/determining-the-bazaar-version-number-from-python-without-calling-bzr
            from bzrlib.branch import BzrBranch
            branch = BzrBranch.open_containing('.')[0]
            revno=str(branch.last_revision_info()[0])+'+bzr'
        except: pass
    else:
        log.warn('Unable to determine revision number (no .git or .bzr here, or getting revision failed).')
        revno='0+na'
    version='1.0.'+revno
    

##
## build options
##
features=['vtk','gts','openmp',('qt5' if QT5 else 'qt4'),'opengl']+(['hdf5'] if not WIN else [])
# disable even openmp for travis, since gcc 4.7 & 4.8 ICE and clang's version there does not support OpenMP yet
if travis: features=[] # quite limited for now, see https://github.com/travis-ci/apt-package-whitelist/issues/779 and https://github.com/travis-ci/apt-package-whitelist/issues/526 
flavor='' #('' if WIN else 'distutils')
if travis: flavor+=('-' if flavor else '')+'travis'
# distribution builds should set not flavor
if PY3 and not DISTBUILD: flavor+=('-' if flavor else '')+'py3'
debug=False
chunkSize=1 # (1 if WIN else 10)
hotCxx=[] # plugins to be compiled separately despite chunkSize>1

# XXX
chunkSize=10
# features+=['noxml']
# QQQ
# features=['noxml']
# flavor='py2test'
if DISTBUILD:
    os.environ['CXX']='clang++'
    os.environ['CC']='clang'
else:
    os.environ['CXX']='g++'
    os.environ['CC']='gcc'

if not DISTBUILD:
    ## arch-specific optimizations
    march='corei7' if WIN else 'native'

##
## end build options
##
if DISTBUILD=='debian': chunkSize=1 # be nice to the builder at launchpad


cxxFlavor=('_'+re.sub('[^a-zA-Z0-9_]','_',flavor) if flavor else '')
execFlavor=('-'+flavor) if flavor else ''
cxxInternalModule='_cxxInternal%s%s'%(cxxFlavor,'_debug' if debug else '')

if 'opengl' in features and ('qt4' not in features and 'qt5' not in features): raise ValueError("The 'opengl' features is only meaningful in conjunction with 'qt4' or 'qt5'.")


#
# install headers and source (in chunks)
#
def wooPrepareHeaders():
    'Copy headers to build-src-tree/woo/ subdirectory'
    if not os.path.exists(pathHeaders): os.makedirs(pathHeaders)
    hpps=sum([glob(pat) for pat in ('lib/*/*.hpp','lib/*/*.hh','lib/multimethods/loki/*.h','core/*.hpp','pkg/*/*.hpp','pkg/*/*.hpp')],[])
    for hpp in hpps:
        d=join(pathHeaders,dirname(hpp))
        if not os.path.exists(d): os.makedirs(d)
        #print(hpp,d)
        shutil.copyfile(hpp,join(pathHeaders,hpp))
def wooPrepareChunks():
    'Make chunks from sources, and install those files to build-src-tree'
    # make chunks from sources
    global chunkSize
    if chunkSize<0: chunkSize=10000
    srcs=[glob('lib/*/*.cpp')+['lib/voro++/voro++.cc'],glob('py/*.cpp'),glob('py/*/*.cpp')]
    if WIN: srcs=[[s] for s in sum(srcs,[])] # compile each file separately even amongst base files
    if 'opengl' in features: srcs+=[glob('gui/qt4/*.cpp')+glob('gui/qt4/*.cc')]
    if 'gts' in features: srcs+=[[f] for f in glob('py/3rd-party/pygts-0.3.1/*.cpp')]
    pkg=glob('pkg/*.cpp')+glob('pkg/*/*.cpp')+glob('pkg/*/*/*.cpp')+glob('core/*.cpp')
    print(srcs,pkg)
    for i in range(0,len(pkg),chunkSize): srcs.append(pkg[i:i+chunkSize])
    hot=[]
    for i in range(len(srcs)):
        hot+=[s for s in srcs[i] if basename(s)[:-4] in hotCxx]
        srcs[i]=[s for s in srcs[i] if basename(s)[:-4] not in hotCxx]
    srcs+=[[h] for h in hot] # add as single files
    #print(srcs)
    # check hash
    import hashlib; h=hashlib.new('sha1'); h.update(str(srcs).encode('utf-8'))
    # exactly the same configuration does not have to be repeated again
    chunksSame=os.path.exists(join(pathSources,h.hexdigest()))
    if not chunksSame and os.path.exists(pathSources): shutil.rmtree(pathSources)
    if not os.path.exists(pathSources):
        os.mkdir(pathSources)
        open(join(pathSources,h.hexdigest()),'w')
    #print(srcs)
    for i,src in enumerate(srcs):
        if len(src)==0: continue
        # ext=('c' if src[0].split('.')[-1]=='c' else 'cpp')
        ext='cpp' # FORCE the .cpp extension so that we don't have to pass -xc++ to the compiler with clang (which chokes at plain c with -std=c++11)
        nameNoExt='' if len(src)>1 else '-'+basename(src[0][:-len(src[0].split('.')[-1])-1])
        chunkPath=join(pathSources,('chunk-%02d%s.%s'%(i,nameNoExt,ext)))
        if not chunksSame:
            f=open(chunkPath,'w')
            for s in src:
                f.write('#include"../%s"\n'%s) # build-src-tree
        else:
            # update timestamp to the newest include
            if not os.path.exists(chunkPath): raise RuntimeError('Chunk configuration identical, but chunk %s not found; delete the build directory to recreate everything.'%chunkPath)
            last=max([os.path.getmtime(s) for s in src])
            #for s in src: print(s,os.path.getmtime(s))
            if last>os.path.getmtime(chunkPath):
                log.info('Updating timestamp of %s (%s -> %s)'%(chunkPath,os.path.getmtime(chunkPath),last+10))
                os.utime(chunkPath,(last+10,last+10))

def wooPrepareQt():
    'Generate Qt files (normally handled by scons); those are only needed with Qt/OpenGL'
    global features
    if 'qt4' not in features and 'qt5' not in features: return
    if QT5 is None: raise ValueError('qt4/qt5 feature enabled, but PyQt4/PyQt5 not importable.')
    if 'qt4' in features and QT5==True:  raise ValueError('qt4 feature enabled, but detected Qt is PyQt5.')
    if 'qt5' in features and QT5==False: raise ValueError('qt5 feature enabled, but detected Qt is PyQt4.')
    QTVER=(5 if QT5 else 4)
    rccInOut=[('gui/qt4/img.qrc','gui/qt4/img_rc.py')]
    uicInOut=[('gui/qt4/controller.ui','gui/qt4/ui_controller.py')]
    mocInOut=[
        ('gui/qt4/GLViewer.hpp','gui/qt4/moc_GLViewer.cc'),
        ('gui/qt4/OpenGLManager.hpp','gui/qt4/moc_OpenGLManager.cc')
    ]
    cxxRccInOut=[('gui/qt4/GLViewer.qrc','gui/qt4/qrc_GLViewer.cc')]
    # stamp for python version, so that files are re-created even if time-stamp is OK but python version is different
    # this is encountered when building debian package for py2 and py3 one after another
    stamp='_pyversion__by_setup.py_'
    currver=str(sys.version_info[:2]) # e.g (2, 7)
    sameVer=os.path.exists(stamp) and (open(stamp,'r').read()==currver)
    if not sameVer: open(stamp,'w').write(currver)
    if WIN:
        # this is ugly
        # pyuic is a batch file, which is not runnable from mingw shell directly
        # find the real exacutable then
        if QTVER==4:
            import PyQt4.uic
            pyuic=PyQt4.uic.__file__[:-12]+'pyuic.py' # strip "__init__.py" form the end
        else:
            # this was never really tested                
            import PyQt5.uic
            pyuic=PyQt5.uic.__file__[:-12]+'pyuic.py' # strip "__init__.py" form the end
    else:
        pyuic='pyuic%d'%QTVER
    for tool0,isPy,opts,inOut,enabled in [
            ('pyrcc%d'%QTVER,False,[] if QT5 else (['-py3'] if PY3 else ['-py2']),rccInOut,True),
            (pyuic,True,['--from-imports'],uicInOut,True),
            ((QT5DIR+'/bin/moc' if QT5 else 'moc'),False,['-DWOO_OPENGL','-DWOO_QT%d'%QTVER],mocInOut,('opengl' in features)),
            ('rcc',False,['-name','GLViewer'],cxxRccInOut,('opengl' in features))
    ]:
        if not enabled: continue
        tool=[distutils.spawn.find_executable(tool0)] # full path the the tool
        if tool[0] is None: raise RuntimError('Tool %s not found?'%tool0)
        for fIn,fOut in inOut:
            # DAMN... Debian needs to run pyuic4 with python2 (even when building with py3k)
            # and right now travis does not build with Qt, so we just call tool directly and rely on the shebang there
            ## run python scripts the same interpreter, needed for virtual environments
            ## if isPy: tool=[sys.executable]+tool
            cmd=tool+opts+[fIn,'-o',fOut]
            # no need to recreate, since source is older
            if sameVer and os.path.exists(fOut) and os.path.getmtime(fIn)<os.path.getmtime(fOut): continue
            log.info(' '.join(cmd))
            status=subprocess.call(cmd)
            if status: raise RuntimeError("Error %d returned when running %s"%(status,' '.join(cmd)))
            if not os.path.exists(fOut): RuntimeError("No output file (though exit status was zero): %s"%(' '.join(cmd)))

def pkgconfig(packages):
    flag_map={'-I':'include_dirs','-L':'library_dirs','-l':'libraries'}
    ret={'library_dirs':[],'include_dirs':[],'libraries':[]}
    for token in subprocess.check_output("pkg-config --libs --cflags %s"%' '.join(packages),shell=True).decode('utf-8').split():
        if token[:2] in flag_map:
            ret.setdefault(flag_map.get(token[:2]),[]).append(token[2:])
        # throw others to extra_link_args
        else: ret.setdefault('extra_link_args',[]).append(token)
    # remove duplicated
    for k,v in ret.items(): ret[k]=list(set(v))
    return ret

log.info('Enabled features: '+(','.join(features)))

# if the following file is missing, we are being run from sdist, which has tree already prepared
# otherwise, install headers, chunks and scripts where they should be
if os.path.exists('examples'):
    wooPrepareQt() # no-op if qt4 or qt5 not in features
    wooPrepareHeaders()
    wooPrepareChunks()
# files are in chunks
cxxSrcs=['py/config.cxx']+glob(join(pathSources,'*.cpp'))+glob(join(pathSources,'*.c'))

###
### preprocessor, compiler, linker flags
###
cppDirs,cppDef,cxxFlags,cxxLibs,linkFlags,libDirs=[],[],[],[],[],[]
##
## general
##
cppDef+=[
    ('WOO_REVISION',revno),
    ('WOO_VERSION',version),
    ('WOO_SOURCE_ROOT','' if DISTBUILD else dirname(os.path.abspath(__file__)).replace('\\','/')),
    ('WOO_BUILD_ROOT',os.path.abspath(pathSourceTree).replace('\\','/')),
    ('WOO_FLAVOR',flavor),
    ('WOO_CXX_FLAVOR',cxxFlavor),
]
cppDef+=[('WOO_'+feature.upper().replace('-','_'),None) for feature in features]
cppDirs+=[pathSourceTree]


cxxStd='c++11'
## this is needed for packaging on Ubuntu 12.04, where gcc 4.6 is the default
if DISTBUILD=='debian':
    # c++0x for gcc == 4.6
    gccVer=bytes(subprocess.check_output(['g++','--version'])).split(b'\n')[0].split()[-1]
    log.info('GCC version is '+gccVer.decode('utf-8'))
    if gccVer.startswith(b'4.6'):
        cxxStd='c++0x'
        log.info('Compiling with gcc 4.6 (%s), using -std=%s. Adding -pedantic.'%(gccVer,cxxStd))
        cxxFlags+=['-pedantic'] # work around for http://gcc.gnu.org/bugzilla/show_bug.cgi?id=50478

cxxFlags+=['-Wall','-fvisibility=hidden','-std='+cxxStd,'-pipe']


cxxLibs+=['m',
    'boost_python%s'%('-py%d%d'%(sys.version_info[0],sys.version_info[1]) if not WIN else ''),
    'boost_system',
    'boost_thread',
    'boost_date_time',
    'boost_filesystem',
    'boost_iostreams',
    'boost_regex',
    'boost_serialization',
    'boost_chrono']
##
## Platform-specific
##
if DISTBUILD:
    # this would be nice, but gcc at launchpad ICEs with that
    # cxxFlags+=['-ftime-report','-fmem-report','-fpre-ipa-mem-report','-fpost-ipa-mem-report']
    pass
if WIN:
    cppDirs+=['c:/MinGW64/include','c:/MinGW64/include/eigen3','c:/MinGW64/include/boost-1_51']
    # avoid warnings from other headers
    # avoid hitting section limit by inlining
    cxxFlags+=['-Wno-strict-aliasing','-Wno-attributes','-finline-functions']     
    boostTag='-mgw47-mt-1_51'
    cxxLibs=[(lib+boostTag if lib.startswith('boost_') else lib) for lib in cxxLibs]
else:
    cppDirs+=['/usr/include/eigen3']
    # we want to use gold with gcc under Linux
    # binutils now require us to select gold explicitly (see https://launchpad.net/ubuntu/saucy/+source/binutils/+changelog)
    if not DISTBUILD: linkFlags+=['-fuse-ld=gold']
    
##
## Debug-specific

# QQQ##
if debug:
    cppDef+=[('WOO_DEBUG',None),]
    cxxFlags+=['-Os']
else:
    cppDef+=[('NDEBUG',None),]
    cxxFlags+=['-g0','-O3']
    if march: cxxFlags+=['-march=%s'%march]
    linkFlags+=['-Wl,--strip-all']
##
## Feature-specific
##
if 'openmp' in features:
    cxxLibs.append('gomp')
    cxxFlags.append('-fopenmp')
if 'hdf5' in features:
    if WIN: raise ValueError('HDF5 not supported under Windows.')
    cxxLibs.append('hdf5_cpp')
    cppDirs+=['/usr/include/hdf5/serial']
if 'opengl' in features:
    if WIN: cxxLibs+=['opengl32','glu32','glut','gle','QGLViewer2']
    else:
        cxxLibs+=['GL','GLU','glut','gle']
        def tryLib(l):
            try:
                # this will for sure fail - either the lib is not found (the first error reported), or we get "undefined reference to main" when the lib is there
                subprocess.check_output(['gcc','-l'+l],stderr=subprocess.STDOUT)
            except (subprocess.CalledProcessError,) as e:
                # print(20*'=','output from gcc -l'+l,20*'=',e.output,60*'=')
                out=e.output.decode('utf-8')
                if 'undefined reference' in out:
                    print('library check: '+l+' found.')
                    return True
                elif '-l'+l in out:
                    print('library check: '+l+' NOT found.')
                    return False
                raise RuntimeError('Library check returned output which does not contain neiter "undefined reference" nor "-l'+l+'".')
        if 'qt4' in features and tryLib('qglviewer-qt4'): cxxLibs+=['qglviewer-qt4']
        elif 'qt5' in features and tryLib('QGLViewer-qt5'): cxxLibs+=['QGLViewer-qt5']
        elif tryLib('QGLViewer'): cxxLibs+=['QGLViewer']
    # qt4 without OpenGL is pure python and needs no additional compile options
    if ('qt4' in features or 'qt5' in features):
        cppDef+=[('QT_CORE_LIB',None),('QT_GUI_LIB',None),('QT_OPENGL_LIB',None),('QT_SHARED',None)]
        if 'qt5' in features: cppDef+=[('QT_WIDGETS_LIB',None)]
        if WIN:
            if 'qt5' in features: raise ValueError('Qt5 build not supported under Windows (yet?)')
            cppDirs+=['c:/MinGW64/include/'+component for component in ('QtCore','QtGui','QtOpenGL','QtXml')]
            cxxLibs+=['QtCore4','QtGui4','QtOpenGL4','QtXml4']
        else:
            if 'qt5' in features:
                cppDirs+=[QT5INC]+[QT5INC+'/'+component for component in  ('QtCore','QtGui','QtOpenGL','QtXml','QtWidgets')]
                cxxLibs+=['Qt5Core','Qt5Gui','Qt5Widgets','Qt5Xml','Qt5OpenGL']
            else:
                cppDirs+=['/usr/include/qt4']+['/usr/include/qt4/'+component for component in ('QtCore','QtGui','QtOpenGL','QtXml')]
                cxxLibs+=['QtCore','QtGui','QtOpenGL','QtXml']
if 'vtk' in features:
    vtks=(glob('/usr/include/vtk-*') if not WIN else glob('c:/MinGW64/include/vtk-*'))
    if not vtks: raise ValueError("No header directory for VTK detected.")
    elif len(vtks)>1: raise ValueError("Multiple header directories for VTK detected: "%','.join(vtks))
    cppDirs+=[vtks[0]]
    # find VTK version from include directory ending in -x.y
    m=re.match(r'.*-(\d)\.(\d+)$',vtks[0])
    if not m: raise ValueError("VTK include directory %s not matching numbers ...-x.y, unable to guess VTK version."%vtks[0])
    vtkMajor,vtkMinor=int(m.group(1)),int(m.group(2))
    if vtkMajor==5:
        cxxLibs+=['vtkCommon','vtkHybrid','vtkRendering','vtkIO','vtkFiltering']
    elif vtkMajor==6:
        suff='-%d.%d'%(vtkMajor,vtkMinor) # library suffix used on Debian, perhaps not used elsewhere?!
        cxxLibs+=['vtkCommonCore'+suff,'vtkCommonDataModel'+suff,'vtkIOXML'+suff]
    else: raise ValueError('Unsupported VTK version %d.x'%vtkMajor)
    if WIN:
        if vtkMajor==6: raise ValueError("VTK6.x not supported under Windows (yet).")
        libDirs+=glob('c:/MinGW64/lib/vtk-*')
        cxxLibs+=['vtksys']
if 'gts' in features:
    c=pkgconfig(['gts'])
    cxxLibs+=['gts']+c['libraries']
    cppDirs+=c['include_dirs']
    libDirs+=c['library_dirs']

## Bug-specific
if 1:
    # see https://gcc.gnu.org/bugzilla/show_bug.cgi?id=48891
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.cpp',delete=False) as tmp:
        tmp.write(b'#include<cmath>\n#include<math.h>\nusing std::isnan;\n')
        tmp.close()
        try: subprocess.check_output(['gcc','-std='+cxxStd,'-c',tmp.name])
        except (subprocess.CalledProcessError,) as e:
            print('Using -DWOO_WORKAROUND_CXX11_MATH_DECL_CONFLICT (auto-detected)')
            cppDef+=[('WOO_WORKAROUND_CXX11_MATH_DECL_CONFLICT',None)]


wooModules=['woo.'+basename(py)[:-3] for py in glob('py/*.py') if basename(py)!='__init__.py']

# compiler-specific flags, if ever needed:
#     http://stackoverflow.com/a/5192738/761090
#class WooBuildExt(distutils.command.build_ext.build_ext):
#    def build_extensions(self):
#        c=self.compiler.compiler_type
#        if re.match(r'.*(gcc|g\+\+)^'):
#            for e in self.extensions:
#                e.extra_compile_args=['-fopenmp']
#                e.extra_link_args=['-lgomp']

setup(name='woo',
    version=version,
    author='Václav Šmilauer',
    author_email='eu@doxos.eu',
    url='http://www.woodem.org',
    description='Discrete dynamic computations, especially granular mechanics.',
    long_description='''Extesible and portable framework primarily for mechanics
of granular materials. Computation parts are written in c++ parallelized using
OpenMP, fully accessible and modifiable from python (ipython console or
scripts). Arbitrarily complex scene can be scripted. Qt-based user interface
is provided, featuring flexible OpenGL display, inspection of all objects
and runtime modification. Parametric preprocessors can be written in pure
python, and batch system can be used to drive parametric studies. New
material models and particle shapes can be added (in c++) without modifying
existing classes.
    
Woo is an evolution of the Yade package
(http://www.launchpad.net/yade), aiming at more flexibility, extensibility,
tighter integration with python and user-friendliness.
    ''',
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Programming Language :: C++',
        'Programming Language :: Python',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Intended Audience :: Science/Research',
        'Development Status :: 4 - Beta'
    ],
    # '' must use join(...) to use native separator
    # otherwise scripts don't get installed!
    # http://stackoverflow.com/questions/13271085/console-scripts-entry-point-ignored
    package_dir={'woo':'py','':join('core','main'),'woo.qt':'gui/qt4','woo.pre':'py/pre','woo.gts':'py/3rd-party/pygts-0.3.1'},
    packages=(
        ['woo','woo._monkey','woo.tests','woo.pre']
        +(['woo.qt'] if ('qt4' in features or 'qt5' in features) else [])
        +(['woo.gts'] if 'gts' in features else [])
    ),
    
    # unfortunately, package_data must be in the same directory as the module
    # they belong to; therefore, they were moved to py/resources
    package_data={'woo':['data/*']},
    
    py_modules=wooModules+['wooMain'],
        ext_modules=[
        Extension('woo.'+cxxInternalModule,
            sources=cxxSrcs,
            include_dirs=cppDirs,
            define_macros=cppDef,
            extra_compile_args=cxxFlags,
            libraries=cxxLibs,
            library_dirs=libDirs,
            extra_link_args=linkFlags,
        ),
    ],
    # works under windows as well now
    # http://stackoverflow.com/questions/13271085/console-scripts-entry-point-ignored
    entry_points={
        'console_scripts':[
            # wwoo on Windows, woo on Linux
            '%swoo%s = wooMain:main'%('w' if WIN else '',execFlavor),
            # wwoo_batch on windows
            # woo-batch on Linux
            '%swoo%s%sbatch = wooMain:batch'%('w' if WIN else '',execFlavor,'_' if WIN else '-'),
        ],
    },
    # woo.__init__ makes symlinks to _cxxInternal, which would not be possible if zipped
    # see http://stackoverflow.com/a/10618900/761090
    zip_safe=False, 
    # source supports both python2 and python3 now, no need for translation
    use_2to3=False,
)

