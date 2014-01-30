#include<woo/core/Field.hpp>
#include<woo/lib/base/CompUtils.hpp>
#include<woo/core/Scene.hpp>

#ifdef WOO_OPENGL
void ScalarRange::reset(){
	mnmx=Vector2r(Inf,-Inf);
	setAutoAdjust(true);
}

void ScalarRange::postLoad(const ScalarRange&,void*attr){
	if(attr==&mnmx && isOk()) setAutoAdjust(false);
	if(isLog() && isSymmetric()) setSymmetric(false);
	cacheLogs();
}

void ScalarRange::cacheLogs(){
	logMnmx[0]=mnmx[0]>0?log(mnmx[0]):0.; logMnmx[1]=mnmx[1]>0?log(mnmx[1]):0;
}

void ScalarRange::adjust(const Real& v){
	if(isLog() && v<0) setLog(false);
	if(isSymmetric()){ if(abs(v)>max(abs(mnmx[0]),abs(mnmx[1])) || !isOk()){ mnmx[0]=-abs(v); mnmx[1]=abs(v); } }
	else {if(v<mnmx[0]) mnmx[0]=v; if(v>mnmx[1]) mnmx[1]=v; }
	if(!(mnmx[0]<=mnmx[1])) mnmx[0]=mnmx[1]; // inverted min/max?
	if(isLog()){
		if(!(mnmx[1]>0)) mnmx[1]=abs(mnmx[1])>0?abs(mnmx[1]):1.; // keep scale if possible
		if((!(mnmx[0]>0)) || (!(mnmx[0]<mnmx[1]))) mnmx[0]=1e-3*mnmx[1];
		cacheLogs();
	}
}


Real ScalarRange::norm(Real v){
	if(isAutoAdjust()) adjust(v);
	if(!isLog()){
		return CompUtils::clamped((v-mnmx[0])/(mnmx[1]-mnmx[0]),0,1);
	} else {
		if(v<=mnmx[0]) return 0;
		return CompUtils::clamped((log(v)-logMnmx[0])/(logMnmx[1]-logMnmx[0]),0,1);
	}	
};

Real ScalarRange::normInv(Real norm){
	if(!isLog()) return mnmx[0]+norm*(mnmx[1]-mnmx[0]);
	else return exp(logMnmx[0]+norm*(logMnmx[1]-logMnmx[0]));
}

Vector3r ScalarRange::color(Real v){
	return CompUtils::mapColor(norm(v),cmap,isReversed());
}

#endif


AlignedBox3r Field::renderingBbox() const {
	AlignedBox3r b;
	for(const shared_ptr<Node>& n: nodes){
		if(!n) continue;
		b.extend(n->pos);
	}
	return b;
}

py::object Field::py_getScene(){
	if(!scene) return py::object();
	else return py::object(static_pointer_cast<Scene>(scene->shared_from_this()));
}



// Node::dataIndexMax=Node::ST_LAST;

