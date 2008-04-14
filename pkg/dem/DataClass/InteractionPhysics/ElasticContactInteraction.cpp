/*************************************************************************
*  Copyright (C) 2004 by Olivier Galizzi                                 *
*  olivier.galizzi@imag.fr                                               *
*                                                                        *
*  This program is free software; it is licensed under the terms of the  *
*  GNU General Public License v2 or later. See file LICENSE for details. *
*************************************************************************/

#include "ElasticContactInteraction.hpp"


ElasticContactInteraction::ElasticContactInteraction()
{
	createIndex();
}

ElasticContactInteraction::~ElasticContactInteraction()
{
}

// void ElasticContactInteraction::postProcessAttributes(bool)
// {
// 
// }


void ElasticContactInteraction::registerAttributes()
{
	SimpleElasticInteraction::registerAttributes();
	REGISTER_ATTRIBUTE(prevNormal);
	REGISTER_ATTRIBUTE(ks);
	REGISTER_ATTRIBUTE(shearForce);
	REGISTER_ATTRIBUTE(initialKn);
	REGISTER_ATTRIBUTE(initialKs);
	REGISTER_ATTRIBUTE(tangensOfFrictionAngle);
//		Real		 kn				// normal elastic constant.
//				,ks				// shear elastic constant.
//				,initialKn			// initial normal elastic constant.
//				,initialKs			// initial shear elastic constant.
//				,equilibriumDistance		// equilibrium distance
//				,initialEquilibriumDistance	// initial equilibrium distance
//				,frictionAngle 			// angle of friction, according to Coulumb criterion
//				,tangensOfFrictionAngle;
//	
//		Vector3r	prevNormal			// unit normal of the contact plane.
//				,normalForce			// normal force applied on a DE
//				,shearForce;			// shear force applied on a DE
}
YADE_PLUGIN();
