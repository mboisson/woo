/*************************************************************************
*  Copyright (C) 2004 by Olivier Galizzi                                 *
*  olivier.galizzi@imag.fr                                               *
*  Copyright (C) 2004 by Janek Kozicki                                   *
*  cosurgi@berlios.de                                                    *
*                                                                        *
*  This program is free software; it is licensed under the terms of the  *
*  GNU General Public License v2 or later. See file LICENSE for details. *
*************************************************************************/

#ifndef BOUNDINGVOLUMEFACTORY_HPP
#define BOUNDINGVOLUMEFACTORY_HPP

#include <yade/yade-core/BoundingVolume.hpp>
#include <yade/yade-core/InteractingGeometry.hpp>
#include <yade/yade-core/Body.hpp>
#include <yade/yade-core/MetaBody.hpp>
#include <yade/yade-core/EngineUnit2D.hpp>

#include <boost/shared_ptr.hpp>
#include <string>

/*! \brief Abstract interface for all bounding volume factories.
	It is used for creating a bounding volume from interaction geometry during runtime.
	This is useful when it's not trivial to build the bounding volume from the interaction model.
	 
	For example if you want to build an AABB from a box which is not initially aligned with the world
	axis, it is not easy to write by hand into the configuration file the center and size of this AABB.
	Instead you can use a BoundingVolumeEngineUnit that will compute for you the correct value.
*/
class BoundingVolumeEngineUnit : public EngineUnit2D
	/*! Method called to build a given bounding volume from a given collision model and a 3D transformation
		\param const shared_ptr<InteractingGeometry>&	the collision model from wich we want to extract the bounding volume
		\param Se3r&					the 3D transformation to apply to the collision model before building the bounding volume
		\param Body*					the Body inside which operation takes place
		\param shared_ptr<BoundingVolume>&		shared pointer to the bounding volume built
	*/
				<
		 			void ,
		 			TYPELIST_4(	  const shared_ptr<InteractingGeometry>&
							, shared_ptr<BoundingVolume>&
							, const Se3r&	// FIXME - remove Se3r, because not everything is supposed to have it. 
									// If some function needs Se3r it must find it through Body*
							, const Body*	// with that - functors have all the data they may need, but it's const, so they can't modify it !
			  			  )
				>
{	
	REGISTER_CLASS_NAME(BoundingVolumeEngineUnit);
	REGISTER_BASE_CLASS_NAME(EngineUnit2D);

};

REGISTER_SERIALIZABLE(BoundingVolumeEngineUnit,false);

#endif // BOUNDINGVOLUMEFACTORY_HPP

