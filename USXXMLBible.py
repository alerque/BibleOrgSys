#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USXXMLBible.py
#
# Module handling compilations of USX Bible books
#
# Copyright (C) 2012-2015 Robert Hunt
# Author: Robert Hunt <Freely.Given.org@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Module for defining and manipulating complete or partial USX Bibles.
"""

from gettext import gettext as _

LastModifiedDate = '2015-02-03' # by RJH
ShortProgName = "USXXMLBibleHandler"
ProgName = "USX XML Bible handler"
ProgVersion = '0.20'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
import multiprocessing

import BibleOrgSysGlobals
from USXFilenames import USXFilenames
from USXXMLBibleBook import USXXMLBibleBook
from Bible import Bible



def t( messageString ):
    """
    Prepends the module name to a error or warning message string if we are in debug mode.
    Returns the new string.
    """
    try: nameBit, errorBit = messageString.split( ': ', 1 )
    except ValueError: nameBit, errorBit = '', messageString
    if BibleOrgSysGlobals.debugFlag or debuggingThisModule:
        nameBit = '{}{}{}: '.format( ShortProgName, '.' if nameBit else '', nameBit )
    return '{}{}'.format( nameBit, _(errorBit) )
# end of t



def USXXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for USX Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number of Bibles found.

    if autoLoad is true and exactly one USX Bible is found,
        returns the loaded USXXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if BibleOrgSysGlobals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("USXXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("USXXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " USXXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ): foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories

    # See if there's an USXBible project here in this given folder
    numFound = 0
    UFns = USXFilenames( givenFolderName ) # Assuming they have standard Paratext style filenames
    if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
    filenameTuples = UFns.getConfirmedFilenames()
    if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
    if BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: print( "  Found {} USX file{}.".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
    if filenameTuples:
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck got", numFound, givenFolderName )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USXXMLBible( givenFolderName )
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if not os.access( tryFolderName, os.R_OK ): # The subfolder is not readable
            logging.warning( _("USXXMLBibleFileCheck: {!r} subfolder is unreadable").format( tryFolderName ) )
            continue
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    USXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ): foundSubfiles.append( something )

        # See if there's an USX Bible here in this folder
        UFns = USXFilenames( tryFolderName ) # Assuming they have standard Paratext style filenames
        if BibleOrgSysGlobals.verbosityLevel > 2: print( UFns )
        filenameTuples = UFns.getConfirmedFilenames()
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "Confirmed:", len(filenameTuples), filenameTuples )
        if BibleOrgSysGlobals.verbosityLevel > 2 and filenameTuples: print( "  Found {} USX files: {}".format( len(filenameTuples), filenameTuples ) )
        elif BibleOrgSysGlobals.verbosityLevel > 1 and filenameTuples: print( "  Found {} USX file{}".format( len(filenameTuples), '' if len(filenameTuples)==1 else 's' ) )
        if filenameTuples:
            foundProjects.append( tryFolderName )
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            uB = USXXMLBible( foundProjects[0] )
            if autoLoadBooks: uB.load() # Load and process the file
            return uB
        return numFound
# end of USXXMLBibleFileCheck



class USXXMLBible( Bible ):
    """
    Class to load and manipulate USX Bibles.

    """
    def __init__( self, givenFolderName, givenName=None, encoding='utf-8' ):
        """
        Create the internal USX Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "USX XML Bible object"
        self.objectTypeString = "USX"

        self.givenFolderName, self.givenName, self.encoding = givenFolderName, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName
        if not self.name: self.name = os.path.basename( self.givenFolderName )
        if not self.name: self.name = os.path.basename( self.givenFolderName[:-1] ) # Remove the final slash
        if not self.name: self.name = "USX Bible"

        # Do a preliminary check on the readability of our folder
        if not os.access( self.givenFolderName, os.R_OK ):
            logging.error( "USXXMLBible: File {!r} is unreadable".format( self.givenFolderName ) )

        # Find the filenames of all our books
        self.USXFilenamesObject = USXFilenames( self.givenFolderName )
        self.possibleFilenameDict = {}
        for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
            self.possibleFilenameDict[BBB] = filename
    # end of USXXMLBible.__init_


    def loadBook( self, BBB, filename=None ):
        """
        Used for multiprocessing.
        """
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USXXMLBible.loadBook( {}, {} )".format( BBB, filename ) )
        if BBB in self.books: return # Already loaded
        if BBB in self.triedLoadingBook:
            logging.warning( "We had already tried loading USX {} for {}".format( BBB, self.name ) )
            return # We've already attempted to load this book
        self.triedLoadingBook[BBB] = True
        if BibleOrgSysGlobals.verbosityLevel > 2 or BibleOrgSysGlobals.debugFlag: print( _("  USXXMLBible: Loading {} from {} from {}...").format( BBB, self.name, self.sourceFolder ) )
        if filename is None: filename = self.possibleFilenameDict[BBB]
        UBB = USXXMLBibleBook( self, BBB )
        UBB.load( filename, self.givenFolderName, self.encoding )
        UBB.validateMarkers()
        #for j, something in enumerate( UBB._processedLines ):
            #print( j, something )
            #if j > 100: break
        #for j, something in enumerate( sorted(UBB._CVIndex) ):
            #print( j, something )
            #if j > 50: break
        #halt
        self.saveBook( UBB )
        #return UBB
    # end of USXXMLBible.loadBook


    def load( self ):
        """
        Load the books.
        """
        def loadSSFData( ssfFilepath, encoding='utf-8' ):
            """Process the SSF data from the given filepath.
                Returns a dictionary."""
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading SSF data from {!r}").format( ssfFilepath ) )
            lastLine, lineCount, status, settingsDict = '', 0, 0, {}
            with open( ssfFilepath, encoding=encoding ) as myFile: # Automatically closes the file when done
                for line in myFile:
                    lineCount += 1
                    if lineCount==1 and line and line[0]==chr(65279): #U+FEFF
                        logging.info( "USXXMLBible.load: Detected UTF-16 Byte Order Marker in {}".format( ssfFilepath ) )
                        line = line[1:] # Remove the Byte Order Marker
                    if line[-1]=='\n': line = line[:-1] # Remove trailing newline character
                    line = line.strip() # Remove leading and trailing whitespace
                    if not line: continue # Just discard blank lines
                    lastLine = line
                    processed = False
                    if status==0 and line=="<ScriptureText>":
                        status = 1
                        processed = True
                    elif status==1 and line=="</ScriptureText>":
                        status = 2
                        processed = True
                    elif status==1 and line[0]=='<' and line.endswith('/>'): # Handle a self-closing (empty) field
                        fieldname = line[1:-3] if line.endswith(' />') else line[1:-2] # Handle it with or without a space
                        if ' ' not in fieldname:
                            settingsDict[fieldname] = ''
                            processed = True
                        elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                            bits = fieldname.split( None, 1 )
                            assert( len(bits)==2 )
                            fieldname = bits[0]
                            attributes = bits[1]
                            #print( "attributes = {!r}".format( attributes) )
                            settingsDict[fieldname] = (contents, attributes)
                            processed = True
                    elif status==1 and line[0]=='<' and line[-1]=='>':
                        ix1 = line.find('>')
                        ix2 = line.find('</')
                        if ix1!=-1 and ix2!=-1 and ix2>ix1:
                            fieldname = line[1:ix1]
                            contents = line[ix1+1:ix2]
                            if ' ' not in fieldname and line[ix2+2:-1]==fieldname:
                                settingsDict[fieldname] = contents
                                processed = True
                            elif ' ' in fieldname: # Some fields (like "Naming") may contain attributes
                                bits = fieldname.split( None, 1 )
                                assert( len(bits)==2 )
                                fieldname = bits[0]
                                attributes = bits[1]
                                #print( "attributes = {!r}".format( attributes) )
                                if line[ix2+2:-1]==fieldname:
                                    settingsDict[fieldname] = (contents, attributes)
                                    processed = True
                    if not processed: logging.error( "Unexpected {!r} line in SSF file".format( line ) )
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "  " + _("Got {} SSF entries:").format( len(settingsDict) ) )
                if BibleOrgSysGlobals.verbosityLevel > 3:
                    for key in sorted(settingsDict):
                        print( "    {}: {}".format( key, settingsDict[key] ) )
            self.ssfDict = settingsDict # We'll keep a copy of just the SSF settings
            self.settingsDict = settingsDict.copy() # This will be all the combined settings
        # end of loadSSFData

        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("USXXMLBible: Loading {} from {}...").format( self.name, self.givenFolderName ) )

        # Do a preliminary check on the contents of our folder
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.givenFolderName ):
            somepath = os.path.join( self.givenFolderName, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ): foundFiles.append( something )
            else: logging.error( "Not sure what {!r} is in {}!".format( somepath, self.givenFolderName ) )
        if foundFolders: logging.info( "USXXMLBible.load: Surprised to see subfolders in {!r}: {}".format( self.givenFolderName, foundFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "USXXMLBible.load: Couldn't find any files in {!r}".format( self.givenFolderName ) )
            return # No use continuing

        if 0: # We don't have a getSSFFilenames function
            # Attempt to load the metadata file
            ssfFilepathList = self.USXFilenamesObject.getSSFFilenames( searchAbove=True, auto=True )
            if len(ssfFilepathList) == 1: # Seems we found the right one
                loadSSFData( ssfFilepathList[0] )

        # Load the books one by one -- assuming that they have regular Paratext style filenames
        # DON'T KNOW WHY THIS DOESN'T WORK
        if 0 and BibleOrgSysGlobals.maxProcesses > 1: # Load all the books as quickly as possible
            parameters = []
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
                parameters.append( BBB )
            #print( "parameters", parameters )
            with multiprocessing.Pool( processes=BibleOrgSysGlobals.maxProcesses ) as pool: # start worker processes
                results = pool.map( self.loadBook, parameters ) # have the pool do our loads
                print( "results", results )
                assert( len(results) == len(parameters) )
                for j, UBB in enumerate( results ):
                    BBB = parameters[j]
                    self.books[BBB] = UBB
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
        else: # Just single threaded
            for BBB,filename in self.USXFilenamesObject.getConfirmedFilenames():
                UBB = USXXMLBibleBook( self, BBB )
                UBB.load( filename, self.givenFolderName, self.encoding )
                UBB.validateMarkers()
                #print( UBB )
                self.saveBook( UBB )
                #self.books[BBB] = UBB
                ## Make up our book name dictionaries while we're at it
                #assumedBookNames = UBB.getAssumedBookNames()
                #for assumedBookName in assumedBookNames:
                    #self.BBBToNameDict[BBB] = assumedBookName
                    #assumedBookNameLower = assumedBookName.lower()
                    #self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    #self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                    #if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "USXXMLBible.load: Didn't find any regularly named USX files in {!r}".format( self.givenFolderName ) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USX file)
                isUSX = False
                thisPath = os.path.join( self.givenFolderName, thisFilename )
                with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                    for line in possibleUSXFile:
                        if line.startswith( '\\id ' ):
                            USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Have possible USX ID {!r}".format( USXId ) )
                            BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USXId )
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "BBB is {!r}".format( BBB ) )
                            isUSX = True
                        break # We only look at the first line
                if isUSX:
                    UBB = USXXMLBibleBook( self, BBB )
                    UBB.load( self.givenFolderName, thisFilename, self.encoding )
                    UBB.validateMarkers()
                    print( UBB )
                    self.books[BBB] = UBB
                    # Make up our book name dictionaries while we're at it
                    assumedBookNames = UBB.getAssumedBookNames()
                    for assumedBookName in assumedBookNames:
                        self.BBBToNameDict[BBB] = assumedBookName
                        assumedBookNameLower = assumedBookName.lower()
                        self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
                        if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
            if self.books: print( "USXXMLBible.load: Found {} irregularly named USX files".format( len(self.books) ) )
        self.doPostLoadProcessing()
    # end of USXXMLBible.load
# end of class USXXMLBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    testData = (
                ("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.3 Exports/USXExports/Projects/MBTV/",),
                ("Matigsalug", "../../../../../Data/Work/VirtualBox_Shared_Folder/PT7.4 Exports/USX Exports/MBTV/",),
                ) # You can put your USX test folder here

    for name, testFolder in testData:
        if os.access( testFolder, os.R_OK ):
            UB = USXXMLBible( testFolder, name )
            UB.load()
            if BibleOrgSysGlobals.verbosityLevel > 0: print( UB )
            if BibleOrgSysGlobals.strictCheckingFlag: UB.check()
            if BibleOrgSysGlobals.commandLineOptions.export: UB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
            #UBErrors = UB.getErrors()
            # print( UBErrors )
            #print( UB.getVersification () )
            #print( UB.getAddedUnits () )
            #for ref in ('GEN','Genesis','GeNeSiS','Gen','MrK','mt','Prv','Xyz',):
                ##print( "Looking for", ref )
                #print( "Tried finding {!r} in {!r}: got {!r}".format( ref, name, UB.getXRefBBB( ref ) ) )
        else: print( "Sorry, test folder {!r} is not readable on this computer.".format( testFolder ) )

    #if BibleOrgSysGlobals.commandLineOptions.export:
    #    if BibleOrgSysGlobals.verbosityLevel > 0: print( "NOTE: This is {} V{} -- i.e., not even alpha quality software!".format( ProgName, ProgVersion ) )
    #       pass

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    multiprocessing.freeze_support() # Multiprocessing support for frozen Windows executables

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of USXXMLBible.py