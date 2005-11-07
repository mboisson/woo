/*************************************************************************
*  Copyright (C) 2004 by Olivier Galizzi                                 *
*  olivier.galizzi@imag.fr                                               *
*                                                                        *
*  This program is free software; it is licensed under the terms of the  *
*  GNU General Public License v2 or later. See file LICENSE for details. *
*************************************************************************/

#ifndef TETRAHEDRONSTEST_HPP
#define TETRAHEDRONSTEST_HPP

#include <yade/yade-core/FileGenerator.hpp>
#include <yade/yade-package-common/Tetrahedron.hpp>

class TetrahedronsTest : public FileGenerator
{
	private :
		Vector3r	 nbTetrahedrons
				,groundSize
				,gravity;

		Real		 minRadius
				,density
				,maxRadius
				,dampingForce
				,disorder
				,dampingMomentum
				,sphereYoungModulus
				,spherePoissonRatio
				,sphereFrictionDeg;

		int		 timeStepUpdateInterval;
		bool		 rotationBlocked;

		void createBox(shared_ptr<Body>& body, Vector3r position, Vector3r extents);
		void createTetrahedron(shared_ptr<Body>& body, int i, int j, int k);
		void createActors(shared_ptr<MetaBody>& rootBody);
		void positionRootBody(shared_ptr<MetaBody>& rootBody);
		
		void loadTRI(shared_ptr<Tetrahedron>& tet, const string& fileName);

	public :
		TetrahedronsTest ();
		~TetrahedronsTest ();
		string generate();

	protected :
		virtual void postProcessAttributes(bool deserializing);
		void registerAttributes();
	REGISTER_CLASS_NAME(TetrahedronsTest);
	REGISTER_BASE_CLASS_NAME(FileGenerator);
};

REGISTER_SERIALIZABLE(TetrahedronsTest,false);

#endif // TETRAHEDRONSTEST_HPP

