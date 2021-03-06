#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# USFXXMLBible.py
#
# Module handling USFX XML Bibles
#
# Copyright (C) 2013-2014 Robert Hunt
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
Module for defining and manipulating complete or partial USFX Bibles.
"""

from gettext import gettext as _

LastModifiedDate = '2014-12-18' # by RJH
ShortProgName = "USFXBible"
ProgName = "USFX XML Bible handler"
ProgVersion = '0.21'
ProgNameVersion = '{} v{}'.format( ProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, sys, logging, multiprocessing
from xml.etree.ElementTree import ElementTree, ParseError

import BibleOrgSysGlobals
from Bible import Bible, BibleBook



filenameEndingsToIgnore = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
extensionsToIgnore = ( 'ASC', 'BAK', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML', 'JAR',
                    'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot



def USFXXMLBibleFileCheck( sourceFolder, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for USFX XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one USFX Bible is found,
        returns the loaded USFXXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck( {}, {}, {} )".format( sourceFolder, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag: assert( sourceFolder and isinstance( sourceFolder, str ) )
    if BibleOrgSysGlobals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( sourceFolder, os.R_OK ):
        logging.critical( _("USFXXMLBibleFileCheck: Given {!r} folder is unreadable").format( sourceFolder ) )
        return False
    if not os.path.isdir( sourceFolder ):
        logging.critical( _("USFXXMLBibleFileCheck: Given {!r} path is not a folder").format( sourceFolder ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " USFXXMLBibleFileCheck: Looking for files in given {}".format( sourceFolder ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( sourceFolder ):
        somepath = os.path.join( sourceFolder, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in filenameEndingsToIgnore:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories
    #print( 'ff', foundFiles )

    # See if there's a USFX project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, sourceFolder, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if "<usfx " not in firstLines[0]:
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck got", numFound, sourceFolder, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = USFXXMLBible( sourceFolder, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( sourceFolder, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    USFXXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( sourceFolder, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundSubfiles.append( something )
        #print( 'fsf', foundSubfiles )

        # See if there's a USFX project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if "<usfx " not in firstLines[0]:
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert( len(foundProjects) == 1 )
            ub = USFXXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
# end of USFXXMLBibleFileCheck



def clean( elementText ):
    """
    Given some text from an XML element (which might be None)
        return a stripped value and with internal CRLF characters replaced by spaces.
    """
    if elementText is not None:
        return elementText.strip().replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
# end of clean



class USFXXMLBible( Bible ):
    """
    Class to load and manipulate USFX Bibles.

    """
    def __init__( self, sourceFolder, givenName=None, encoding='utf-8' ):
        """
        Create the internal USFX Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "USFX XML Bible object"
        self.objectTypeString = "USFX"

        self.sourceFolder, self.givenName, self.encoding = sourceFolder, givenName, encoding # Remember our parameters

        # Now we can set our object variables
        self.name = self.givenName
        if not self.name: self.name = os.path.basename( self.sourceFolder )
        if not self.name: self.name = os.path.basename( self.sourceFolder[:-1] ) # Remove the final slash
        if not self.name: self.name = "USFX Bible"
        if self.name.endswith( '_usfx' ): self.name = self.name[:-5] # Remove end of name for Haiola projects

        # Do a preliminary check on the readability of our folder
        if not os.access( self.sourceFolder, os.R_OK ):
            logging.error( "USFXXMLBible: Folder {!r} is unreadable".format( self.sourceFolder ) )

        # Do a preliminary check on the contents of our folder
        self.sourceFilename = self.sourceFilepath = None
        foundFiles, foundFolders = [], []
        for something in os.listdir( self.sourceFolder ):
            somepath = os.path.join( self.sourceFolder, something )
            if os.path.isdir( somepath ): foundFolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in filenameEndingsToIgnore:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in extensionsToIgnore: # Compare without the first dot
                    foundFiles.append( something )
            else: logging.error( "Not sure what {!r} is in {}!".format( somepath, self.sourceFolder ) )
        if foundFolders: logging.info( "USFXXMLBible: Surprised to see subfolders in {!r}: {}".format( self.sourceFolder, foundFolders ) )
        if not foundFiles:
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "USFXXMLBible: Couldn't find any files in {!r}".format( self.sourceFolder ) )
            return # No use continuing

        #print( self.sourceFolder, foundFolders, len(foundFiles), foundFiles )
        numFound = 0
        for thisFilename in sorted( foundFiles ):
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, sourceFolder, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if "<usfx " not in firstLines[0]:
                continue
            lastFilenameFound = thisFilename
            numFound += 1
        if numFound:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "USFXXMLBible got", numFound, sourceFolder, lastFilenameFound )
            if numFound == 1:
                self.sourceFilename = lastFilenameFound
                self.sourceFilepath = os.path.join( self.sourceFolder, self.sourceFilename )
        elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )
    # end of USFXXMLBible.__init_


    def load( self ):
        """
        Load the XML data file -- we should already know the filepath.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1:
            print( _("USFXXMLBible: Loading {} from {}...").format( self.name, self.sourceFolder ) )

                                #if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  It seems we have {}...").format( BBB ) )
                        #self.thisBook = BibleBook( self, BBB )
                        #self.thisBook.objectNameString = "OSIS XML Bible Book object"
                        #self.thisBook.objectTypeString = "OSIS"
                        #self.haveBook = True

        try: self.tree = ElementTree().parse( self.sourceFilepath )
        except ParseError:
            errorString = sys.exc_info()[1]
            logging.critical( "USFXXMLBible.load: failed loading the xml file {}: {!r}.".format( self.sourceFilepath, errorString ) )
            return
        if BibleOrgSysGlobals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        # Find the main (osis) container
        if self.tree.tag == 'usfx':
            location = "USFX file"
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location, '4f6h' )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location, '1wk8' )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.tree.items():
                #print( "attrib", repr(attrib), repr(value) )
                if attrib.endswith("SchemaLocation"):
                    self.schemaLocation = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
            BBB = C = V = None
            for element in self.tree:
                #print( "element", repr(element.tag) )
                sublocation = element.tag + " " + location
                if element.tag == 'languageCode':
                    self.languageCode = element.text
                    BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'cff3' )
                    BibleOrgSysGlobals.checkXMLNoAttributes( element, sublocation, 'des1' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, 'dwf2' )
                elif element.tag == 'book':
                    self.loadBook( element )
                    ##BibleOrgSysGlobals.checkXMLNoSubelements( element, sublocation, '54f2' )
                    #BibleOrgSysGlobals.checkXMLNoTail( element, sublocation, 'hd35' )
                    ## Process the attributes
                    #idField = bookStyle = None
                    #for attrib,value in element.items():
                        #if attrib=='id' or attrib=='code':
                            #idField = value # Should be USFM bookcode (not like BBB which is BibleOrgSys BBB bookcode)
                            ##if idField != BBB:
                            ##    logging.warning( _("Unexpected book code ({}) in {}").format( idField, sublocation ) )
                        #elif attrib=='style':
                            #bookStyle = value
                        #else:
                            #logging.warning( _("gfw2 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                else:
                    logging.warning( _("dbw1 Unprocessed {} element after {} {}:{} in {}").format( element.tag, BBB, C, V, sublocation ) )
                    #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )

        if not self.books: # Didn't successfully load any regularly named books -- maybe the files have weird names??? -- try to be intelligent here
            if BibleOrgSysGlobals.verbosityLevel > 2:
                print( "USFXXMLBible.load: Didn't find any regularly named USFX files in {!r}".format( self.sourceFolder ) )
            for thisFilename in foundFiles:
                # Look for BBB in the ID line (which should be the first line in a USFX file)
                isUSFX = False
                thisPath = os.path.join( self.sourceFolder, thisFilename )
                with open( thisPath ) as possibleUSXFile: # Automatically closes the file when done
                    for line in possibleUSXFile:
                        if line.startswith( '\\id ' ):
                            USXId = line[4:].strip()[:3] # Take the first three non-blank characters after the space after id
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Have possible USFX ID {!r}".format( USXId ) )
                            BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( USXId )
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "BBB is {!r}".format( BBB ) )
                            isUSFX = True
                        break # We only look at the first line
                if isUSFX:
                    UBB = USFXXMLBibleBook( self, BBB )
                    UBB.load( self.sourceFolder, thisFilename, self.encoding )
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
            if self.books: print( "USFXXMLBible.load: Found {} irregularly named USFX files".format( len(self.books) ) )
        self.doPostLoadProcessing()
    # end of USFXXMLBible.load


    def loadBook( self, bookElement ):
        """
        Load the book container from the XML data file.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3:
            print( _("USFXXMLBible.loadBook: Loading {} from {}...").format( self.name, self.sourceFolder ) )
        assert( bookElement.tag == 'book' )
        mainLocation = self.name + " USFX book"

        # Process the attributes first
        bookCode = None
        for attrib,value in bookElement.items():
            if attrib == 'id':
                bookCode = value
            else:
                logging.warning( "bce3 Unprocessed {} attribute ({}) in {}".format( attrib, value, mainLocation ) )
        BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromUSFM( bookCode )
        mainLocation = "{} USFX {} book".format( self.name, BBB )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( _("USFXXMLBible.loadBook: Loading {} from {}...").format( BBB, self.name ) )
        BibleOrgSysGlobals.checkXMLNoText( self.tree, mainLocation, '4f6h' )
        BibleOrgSysGlobals.checkXMLNoTail( self.tree, mainLocation, '1wk8' )

        # Now create our actual book
        self.thisBook = BibleBook( self, BBB )
        self.thisBook.objectNameString = "USFX XML Bible Book object"
        self.thisBook.objectTypeString = "USFX"

        C = V = '0'
        for element in bookElement:
            #print( "element", repr(element.tag) )
            location = "{} of {} {}:{}".format( element.tag, mainLocation, BBB, C, V )
            if element.tag == 'id':
                idText = clean( element.text )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'vsg3' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ksq2' )
                for attrib,value in element.items():
                    if attrib == 'id':
                        assert( value == bookCode )
                    else:
                        logging.warning( _("vsg4 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                self.thisBook.addLine( 'id', bookCode + ((' '+idText) if idText else '') )
            elif element.tag == 'ide':
                ideText = clean( element.text )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'jsa0' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ls01' )
                charset = None
                for attrib,value in element.items():
                    if attrib == 'charset': charset = value
                    else:
                        logging.warning( _("jx53 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                self.thisBook.addLine( 'ide', charset + ((' '+ideText) if ideText else '') )
            elif element.tag == 'h':
                hText = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'dj35' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'hs35' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'hs32' )
                self.thisBook.addLine( 'h', clean(hText) )
            elif element.tag == 'toc':
                tocText = element.text
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ss13' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'js13' )
                level = None
                for attrib,value in element.items():
                    if attrib == 'level': # Seems compulsory
                        level = value
                    else:
                        logging.warning( _("dg36 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                self.thisBook.addLine( 'toc'+level, clean(tocText) )
            elif element.tag == 'c':
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'ks35' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'gs35' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kdr3' ) # This is a milestone
                for attrib,value in element.items():
                    if attrib == 'id':
                        C, V = value, '0'
                    else:
                        logging.warning( _("hj52 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                self.thisBook.addLine( 'c', C )
            elif element.tag == 's':
                sText = clean( element.text )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'wxg0' )
                level = None
                for attrib,value in element.items():
                    if attrib == 'level': # Seems optional
                        level = value
                    else:
                        logging.warning( _("bdy6 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                marker = 's'
                if level: marker += level
                self.thisBook.addLine( marker, sText )
                for subelement in element:
                    #print( "subelement", repr(subelement.tag) )
                    sublocation = subelement.tag + " of " + location
                    if subelement.tag == 'f':
                        self.loadFootnote( subelement, sublocation, BBB, C, V )
                    elif subelement.tag == 'x':
                        self.loadCrossreference( subelement, sublocation )
                    elif subelement.tag == 'fig':
                        self.loadFigure( subelement, sublocation )
                    elif subelement.tag == 'table':
                        self.loadTable( subelement, sublocation )
                    elif subelement.tag in ('add','it','bd','bdit','sc',):
                        self.loadCharacterFormatting( subelement, sublocation, BBB, C, V )
                    elif subelement.tag == 'optionalLineBreak':
                        print( "What is loadBook optionalLineBreak?" )
                    else:
                        logging.warning( _("jx9q Unprocessed {} element after {} {}:{} in {}").format( subelement.tag, BBB, C, V, sublocation ) )
            elif element.tag in ('p','q','d',):
                V = self.loadParagraph( element, location, BBB, C )
            elif element.tag == 'b':
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'ks35' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'gs35' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'nd04' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kdr3' )
                self.thisBook.addLine( 'b', '' )
            elif element.tag in ('cl','cp'): # Simple single-line paragraph-level markers
                marker, text = element.tag, clean(element.text)
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'od01' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'gd92' )
                idField = None
                for attrib,value in element.items():
                    if attrib == 'id': idField = value
                    else:
                        logging.warning( _("dv35 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                if idField and text is None:
                    text = idField
                else:
                    logging.warning( _("dve4 Unprocessed idField ({}) in {}").format( idField, location ) )
                if text is None:
                    logging.critical( "Why is {} empty at {}".format( marker, location ) )
                assert( text is not None )
                self.thisBook.addLine( marker, text )
            elif element.tag == 'table':
                self.loadTable( element, location )
            elif element.tag == 've': # What's this in Psalms: <c id="4" /><ve /><d>For the Chief Musician; on stringed instruments. A Psalm of David.</d>
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'kds3' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ks29' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'kj24' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'js91' )
                #self.thisBook.addLine( 'b', '' )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Ignoring 've' field", BBB, C, V )
            else:
                logging.critical( _("caf2 Unprocessed {} element after {} {}:{} in {}").format( element.tag, BBB, C, V, location ) )
                #self.addPriorityError( 1, c, v, _("Unprocessed {} element").format( element.tag ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        self.saveBook( self.thisBook )
    # end of USFXXMLBible.loadBook


    def loadParagraph( self, paragraphElement, paragraphLocation, BBB, C ):
        """
        Load the paragraph (p or q) container from the XML data file.
        """
        #if BibleOrgSysGlobals.verbosityLevel > 3:
            #print( _("USFXXMLBible.loadParagraph: Loading {} from {}...").format( self.name, self.sourceFolder ) )

        V = None
        pTag, pText = paragraphElement.tag, clean(paragraphElement.text)
        BibleOrgSysGlobals.checkXMLNoTail( paragraphElement, paragraphLocation, 'vsg7' )

        # Process the attributes first
        sfm = level = style = None
        for attrib,value in paragraphElement.items():
            if attrib == 'sfm': sfm = value
            elif attrib == 'level': level = value
            elif attrib == 'style': style = value
            else:
                logging.warning( "vfh4 Unprocessed {} attribute ({}) in {}".format( attrib, value, paragraphLocation ) )

        if sfm:
            assert( pTag == 'p' )
            pTag = sfm
        if level:
            #assert( pTag == 'q' ) # Could also be mt, etc.
            pTag += level
        if style:
            #print( repr(pTag), repr(pText), repr(style) )
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Ignoring {!r} style".format( style ) )

        self.thisBook.addLine( pTag, '' if pText is None else pText )

        for element in paragraphElement:
            location = element.tag + " of " + paragraphLocation
            #print( "element", repr(element.tag) )
            if element.tag == 'v': # verse milestone
                vTail = clean( element.tail ) # Main verse text
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'crc2' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'lct3' )
                lastV, V = V, None
                for attrib,value in element.items():
                    if attrib == 'id':
                        V = value
                    else:
                        logging.warning( _("cbs2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                assert( V is not None )
                assert( V )
                self.thisBook.addLine( 'v', V + ((' '+vTail) if vTail else '' ) )
            elif element.tag == 've': # verse end milestone -- we can just ignore this
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'lsc3' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'mfy4' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'bd24' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'ks35' )
            elif element.tag == 'fig':
                self.loadFigure( element, location )
            elif element.tag == 'table':
                self.loadTable( element, location )
            elif element.tag == 'f':
                #print( "USFX.loadParagraph Found footnote at", paragraphLocation, C, V, repr(element.text) )
                self.loadFootnote( element, location, BBB, C, V )
            elif element.tag == 'x':
                #print( "USFX.loadParagraph Found xref at", paragraphLocation, C, V, repr(element.text) )
                self.loadCrossreference( element, location )
            elif element.tag in ('add','nd','wj','rq','sig','sls','bk','k','tl','vp','pn','qs','qt','em','it','bd','bdit','sc','no',): # character formatting
                self.loadCharacterFormatting( element, location, BBB, C, V )
            elif element.tag == 'cs': # character style -- seems like a USFX hack
                text, tail = clean(element.text), clean(element.tail)
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'kf92' )
                sfm = None
                for attrib,value in element.items():
                    if attrib == 'sfm': sfm = value
                    else:
                        logging.warning( _("sh29 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                if sfm not in ('w','ior',): print( "cs sfm got", repr(sfm) )
                self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}'.format( sfm, text, sfm, (' '+tail) if tail else '' ) )
            elif element.tag in ('cp',): # Simple single-line paragraph-level markers
                marker, text = element.tag, clean(element.text)
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'kdf0' )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'lkj1' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'da13' )
                self.thisBook.addLine( marker, text )
            elif element.tag == 'ref': # encoded reference -- seems like a USFX hack
                text, tail = clean(element.text), clean(element.tail)
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'bd83' )
                target = None
                for attrib,value in element.items():
                    if attrib == 'tgt': target = value
                    else:
                        logging.warning( _("be83 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                #if target not in ('w','ior',): print( "ref sfm got", repr(sfm) )
                self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}{}'.format( element.tag, target, element.tag, text, (' '+tail) if tail else '' ) )
                #print( "Saved", '\\{} {}\\{}*{}{}'.format( element.tag, target, element.tag, text, (' '+tail) if tail else '' ) )
            elif element.tag == 'optionalLineBreak':
                print( "What is loadParagraph optionalLineBreak?" )
                if BibleOrgSysGlobals.debugFlag: halt
            elif element.tag == 'milestone': # e.g., <milestone sfm="pb" attribute=""/> (pb = explicit page break)
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'jzx2' )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ms23' )
                BibleOrgSysGlobals.checkXMLNoSubelements( element, location, 'dw24' )
                sfm = None
                for attrib,value in element.items():
                    if attrib == 'sfm': sfm = value
                    else:
                        logging.warning( _("mcd2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                if sfm not in ('pb',): print( "milestone sfm got", repr(sfm) )
                self.thisBook.addLine( sfm, '' )
            else:
                logging.warning( _("df45 Unprocessed {} element after {} {}:{} in {}").format( repr(element.tag), self.thisBook.BBB, C, V, location ) )
        return V
    # end of USFXXMLBible.loadParagraph


    def loadCharacterFormatting( self, element, location, BBB, C, V ):
        """
        """
        marker, text, tail = element.tag, clean(element.text), clean(element.tail)
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'sd12' )
        self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, text ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            #print( "element", repr(element.tag) )
            if subelement.tag == 'f':
                #print( "USFX.loadParagraph Found footnote at", sublocation, C, V, repr(subelement.text) )
                self.loadFootnote( subelement, sublocation, BBB, C, V )
            else:
                logging.warning( _("sf31 Unprocessed {} element after {} {}:{} in {}").format( repr(subelement.tag), self.thisBook.BBB, C, V, location ) )
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
        self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, (' '+tail) if tail else '' ) )
    # end of USFXXMLBible.loadCharacterFormatting


    def loadFigure( self, element, location ):
        """
        """
        BibleOrgSysGlobals.checkXMLNoText( element, location, 'ff36' )
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'cf35' )
        figDict = { 'description':'', 'catalog':'', 'size':'', 'location':'', 'copyright':'', 'caption':'', 'reference':'' }
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            figTag, figText = subelement.tag, clean(subelement.text)
            assert( figTag in figDict )
            figDict[figTag] = '' if figText is None else figText
            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'jkf5' )
            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'ld18' )
            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'hb46' )
        newString = ''
        for j,tag in enumerate( ('description', 'catalog', 'size', 'location', 'copyright', 'caption', 'reference',) ):
            newString += ('' if j==0 else '|') + figDict[tag]
        figTail = clean( element.tail )
        self.thisBook.appendToLastLine( ' \\fig {}\\fig*{}'.format( newString, (' '+figTail) if figTail else '' ) )
    # end of USFXXMLBible.loadFigure


    def loadTable( self, element, location ):
        """
        """
        BibleOrgSysGlobals.checkXMLNoText( element, location, 'kg92' )
        BibleOrgSysGlobals.checkXMLNoTail( element, location, 'ka92' )
        BibleOrgSysGlobals.checkXMLNoAttributes( element, location, 'ks63' )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            if subelement.tag == 'tr':
                #print( "table", sublocation )
                self.thisBook.addLine( 'tr', '' )
                BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'sg32' )
                BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'dh82' )
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'mniq' )
                for sub2element in subelement:
                    sub2location = sub2element.tag + " of " + sublocation
                    tag, text = sub2element.tag, clean(sub2element.text)
                    assert( tag in ('th', 'thr', 'tc', 'tcr',) )
                    BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location, 'ah82' )
                    BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'ka63' )
                    level = None
                    for attrib,value in sub2element.items():
                        if attrib == 'level': level = value
                        else:
                            logging.warning( _("vx25 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
                    marker = tag + (level if level else '')
                    self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, text ) )
            else:
                logging.warning( _("kv64 Unprocessed {} element after {} {}:{} in {}").format( subelement.tag, self.thisBook.BBB, C, V, sublocation ) )
    # end of USFXXMLBible.loadTable


    def loadFootnote( self, element, location, BBB, C, V ):
        """
        Handles footnote fields, including xt field.
        """
        text, tail = clean(element.text), clean(element.tail)
        caller = None
        for attrib,value in element.items():
            if attrib == 'caller':
                caller = value
            else:
                logging.warning( _("dg35 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
        self.thisBook.appendToLastLine( ' \\f {}{}'.format( caller, (' '+text) if text else '' ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            marker, fText, fTail = subelement.tag, clean(subelement.text), clean(subelement.tail)
            #print( "USFX.loadFootnote", repr(caller), repr(text), repr(tail), repr(marker), repr(fText), repr(fTail) )
            #if BibleOrgSysGlobals.verbosityLevel > 0 and marker not in ('ref','fr','ft','fq','fv','fk','fqa','it','bd','rq',):
                #print( "USFX.loadFootnote found", repr(caller), repr(marker), repr(fText), repr(fTail) )
            if BibleOrgSysGlobals.debugFlag: assert( marker in ('ref','fr','ft','fq','fv','fk','fqa','it','bd','rq','xt',) )
            if marker=='ref':
                assert( fText )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ls13' )
                target = None
                for attrib,value in subelement.items():
                    if attrib == 'tgt': target = value
                    else:
                        logging.warning( _("gs35 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                if target:
                    self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}'.format( marker, target, marker, fText ) )
                else: halt
            else:
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'dq54' )
                self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, fText ) )
                if marker=='xt' or marker[0]=='f': # Starts with f, e.g., fr, ft
                    for sub2element in subelement:
                        sub2location = sub2element.tag + " of " + sublocation
                        marker2, fText2, fTail2 = sub2element.tag, clean(sub2element.text), clean(sub2element.tail)
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'js72' )
                        if marker2 == 'ref':
                            #print( sub2location )
                            if fText2:
                                #print( 'ft2', marker2, repr(fText2), repr(fTail2), sub2location )
                                self.thisBook.appendToLastLine( fText2 )
                            target = None
                            for attrib,value in sub2element.items():
                                if attrib == 'tgt': target = value # OSIS style reference, e.g., '1SA.27.8'
                                else:
                                    logging.warning( _("hd52 Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                            if target:
                                #print( 'tg', marker2, repr(target) )
                                self.thisBook.appendToLastLine( ' \\{} {}'.format( marker2, target ) )
                            else:
                                if debuggingThisModule: halt
                        elif marker2 in ('add','nd','wj','rq','sig','sls','bk','k','tl','vp','pn','qs','qt','em','it','bd','bdit','sc','no',): # character formatting
                            self.loadCharacterFormatting( sub2element, sub2location, BBB, C, V )
                        else:
                            print( 'Ignored marker2', repr(marker2), BBB, C, V )
                            if debuggingThisModule: halt
                        if fTail2: self.thisBook.appendToLastLine( fTail2 )
                elif marker in ('add','nd','wj','rq','sig','sls','bk','k','tl','vp','pn','qs','qt','em','it','bd','bdit','sc','no',): # character formatting
                    self.loadCharacterFormatting( subelement, sublocation, BBB, C, V )
                else:
                    print( 'Ignored marker', repr(marker), BBB, C, V )
                    halt
            if fTail:
                self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, fTail ) )
        self.thisBook.appendToLastLine( '\\f*{}'.format( (' '+tail) if tail else '' ) )
    # end of USFXXMLBible.loadFootnote


    def loadCrossreference( self, element, location ):
        """
        Has to handle: <x caller="+"><ref tgt="EXO.30.12">Exodus 30:12</ref></x>
        """
        text, tail = clean(element.text), clean(element.tail)
        caller = None
        for attrib,value in element.items():
            if attrib == 'caller':
                caller = value
            else:
                logging.warning( _("fhj2 Unprocessed {} attribute ({}) in {}").format( attrib, value, location ) )
        self.thisBook.appendToLastLine( ' \\x {}'.format( caller ) )
        for subelement in element:
            sublocation = subelement.tag + " of " + location
            marker, xText, xTail = subelement.tag, clean(subelement.text), clean(subelement.tail)
            #print( "USFX.loadCrossreference", repr(caller), repr(text), repr(tail), repr(marker), repr(xText), repr(xTail) )
            #if BibleOrgSysGlobals.verbosityLevel > 0 and marker not in ('ref','xo','xt',):
                #print( "USFX.loadCrossreference found", repr(caller), repr(marker), repr(xText), repr(xTail) )
            if BibleOrgSysGlobals.debugFlag: assert( marker in ('ref','xo','xt',) )
            if marker=='ref':
                assert( xText )
                BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 's1sd' )
                target = None
                for attrib,value in subelement.items():
                    if attrib == 'tgt': target = value
                    else:
                        logging.warning( _("aj41 Unprocessed {} attribute ({}) in {}").format( attrib, value, sublocation ) )
                if target:
                    self.thisBook.appendToLastLine( ' \\{} {}\\{}*{}'.format( marker, target, marker, xText ) )
                else: halt
            else:
                BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'sc35' )
                self.thisBook.appendToLastLine( ' \\{} {}'.format( marker, xText ) )
                if marker[0] == 'x': # Starts with x, e.g., xo, xt
                    for sub2element in subelement:
                        sub2location = sub2element.tag + " of " + sublocation
                        marker2, xText2, xTail2 = sub2element.tag, clean(sub2element.text), clean(sub2element.tail)
                        BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'fs63' )
                        if marker2=='ref':
                            if xText2:
                                #print( 'xt2', marker2, repr(xText2), repr(xTail2), sub2location )
                                self.thisBook.appendToLastLine( xText2 )
                            target = None
                            for attrib,value in sub2element.items():
                                if attrib == 'tgt': target = value
                                else:
                                    logging.warning( _("gs34 Unprocessed {} attribute ({}) in {}").format( attrib, value, sub2location ) )
                            if target: self.thisBook.appendToLastLine( ' \\{} {}'.format( marker2, target ) )
                            else: halt
                        else: halt
                        if xTail2: self.thisBook.appendToLastLine( xTail2 )
                else: halt
            if xTail:
                self.thisBook.appendToLastLine( '\\{}*{}'.format( marker, xTail ) )
        self.thisBook.appendToLastLine( '\\x*{}'.format( (' '+tail) if tail else '' ) )
    #end of USFXXMLBible.loadCrossreference
# end of class USFXXMLBible



def demo():
    """
    Demonstrate reading and checking some Bible databases.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    testData = (
                ('ASV', "Tests/DataFilesForTests/USFXTest1/"),
                ("Tst", "../../../../../Data/Work/Bibles/Formats/USFX/",),
                ("AGM", "../../../../../Data/Work/Bibles/USFX Bibles/Haiola USFX test versions/agm_usfx/",),
                ("HBO", "../../../../../Data/Work/Bibles/USFX Bibles/Haiola USFX test versions/hbo_usfx/",),
                ("ZIA", "../../../../../Data/Work/Bibles/USFX Bibles/Haiola USFX test versions/zia_usfx/",),
                ) # You can put your USFX test folder here

    for name, testFolder in testData:
        if os.access( testFolder, os.R_OK ):
            UB = USFXXMLBible( testFolder, name )
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
# end of USFXXMLBible.py