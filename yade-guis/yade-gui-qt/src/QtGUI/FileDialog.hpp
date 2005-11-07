/*************************************************************************
*  Copyright (C) 2004 by Olivier Galizzi                                 *
*  olivier.galizzi@imag.fr                                               *
*                                                                        *
*  This program is free software; it is licensed under the terms of the  *
*  GNU General Public License v2 or later. See file LICENSE for details. *
*************************************************************************/

#ifndef FILEDIALOG_HPP
#define FILEDIALOG_HPP

#include <string>
#include <qfiledialog.h>
#include <qstring.h>

using namespace std;

class FileDialog : public QFileDialog
{
	public :
		FileDialog (const QString& directory,const QString& filters,const string& caption,QWidget* parent);
		virtual ~FileDialog ();
	
		static string getOpenFileName(const string& directory,const string& filters,const string& caption,QWidget* parent,string& selectedFilter );
		static string getSaveFileName(const string& directory,const string& filters,const string& caption,QWidget* parent,string& selectedFilter );
		static string getExistingDirectory ( const string& directory,const string& caption,QWidget* parent);
};

#endif // FILEDIALOG_HPP

