#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# OSISXMLBible.py
#
# Module handling OSIS XML Bibles
#
# Copyright (C) 2010-2015 Robert Hunt
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
Module handling the reading and import of OSIS XML Bibles.

Unfortunately, the OSIS specification (designed by committee for many different tasks)
    allows many different ways of encoding Bibles so the variations are very many.

This is a quickly updated version of an early module,
    and it's both ugly and fragile  :-(

Updated Sept 2013 to also handle Kahunapule's "modified OSIS".
"""

from gettext import gettext as _

LastModifiedDate = '2015-04-18' # by RJH
ShortProgName = "OSISBible"
ProgName = "OSIS XML Bible format handler"
ProgVersion = '0.47'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import logging, os
from xml.etree.ElementTree import ElementTree

import BibleOrgSysGlobals
from ISO_639_3_Languages import ISO_639_3_Languages
from USFMMarkers import USFM_BIBLE_PARAGRAPH_MARKERS
from Bible import Bible, BibleBook


FILENAME_ENDINGS_TO_IGNORE = ('.ZIP.GO', '.ZIP.DATA',) # Must be UPPERCASE
EXTENSIONS_TO_IGNORE = ( 'ASC', 'BAK', 'BBLX', 'BC', 'CCT', 'CSS', 'DOC', 'DTS', 'HTM','HTML', 'JAR',
                    'LDS', 'LOG', 'MYBIBLE', 'NT','NTX', 'ODT', 'ONT','ONTX', 'OSIS', 'OT','OTX', 'PDB',
                    'STY', 'SSF', 'TXT', 'USFM', 'USX', 'VRS', 'YET', 'ZIP', ) # Must be UPPERCASE and NOT begin with a dot


# Get the data tables that we need for proper checking
ISOLanguages = ISO_639_3_Languages().loadData()


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


def OSISXMLBibleFileCheck( givenFolderName, strictCheck=True, autoLoad=False, autoLoadBooks=False ):
    """
    Given a folder, search for OSIS XML Bible files or folders in the folder and in the next level down.

    Returns False if an error is found.

    if autoLoad is false (default)
        returns None, or the number found.

    if autoLoad is true and exactly one OSIS Bible is found,
        returns the loaded OSISXMLBible object.
    """
    if BibleOrgSysGlobals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck( {}, {}, {} )".format( givenFolderName, strictCheck, autoLoad ) )
    if BibleOrgSysGlobals.debugFlag: assert( givenFolderName and isinstance( givenFolderName, str ) )
    if BibleOrgSysGlobals.debugFlag: assert( autoLoad in (True,False,) )

    # Check that the given folder is readable
    if not os.access( givenFolderName, os.R_OK ):
        logging.critical( _("OSISXMLBibleFileCheck: Given {!r} folder is unreadable").format( givenFolderName ) )
        return False
    if not os.path.isdir( givenFolderName ):
        logging.critical( _("OSISXMLBibleFileCheck: Given {!r} path is not a folder").format( givenFolderName ) )
        return False

    # Find all the files and folders in this folder
    if BibleOrgSysGlobals.verbosityLevel > 3: print( " OSISXMLBibleFileCheck: Looking for files in given {}".format( givenFolderName ) )
    foundFolders, foundFiles = [], []
    for something in os.listdir( givenFolderName ):
        somepath = os.path.join( givenFolderName, something )
        if os.path.isdir( somepath ): foundFolders.append( something )
        elif os.path.isfile( somepath ):
            somethingUpper = something.upper()
            somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
            ignore = False
            for ending in FILENAME_ENDINGS_TO_IGNORE:
                if somethingUpper.endswith( ending): ignore=True; break
            if ignore: continue
            if not somethingUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                foundFiles.append( something )
    if '__MACOSX' in foundFolders:
        foundFolders.remove( '__MACOSX' )  # don't visit these directories
    #print( 'ff', foundFiles )

    # See if there's an OSIS project here in this folder
    numFound = 0
    looksHopeful = False
    lastFilenameFound = None
    for thisFilename in sorted( foundFiles ):
        if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
            firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, givenFolderName, numLines=3 )
            if not firstLines or len(firstLines)<2: continue
            if not firstLines[0].startswith( '<?xml version="1.0"' ) \
            and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "OB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                continue
            if not (firstLines[1].startswith( '<osis ' ) or firstLines[2].startswith( '<osis ' )):
                continue
        lastFilenameFound = thisFilename
        numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck got", numFound, givenFolderName, lastFilenameFound )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            ub = OSISXMLBible( givenFolderName, lastFilenameFound )
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
    elif looksHopeful and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Looked hopeful but no actual files found" )

    # Look one level down
    numFound = 0
    foundProjects = []
    for thisFolderName in sorted( foundFolders ):
        tryFolderName = os.path.join( givenFolderName, thisFolderName+'/' )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( "    OSISXMLBibleFileCheck: Looking for files in {}".format( tryFolderName ) )
        foundSubfolders, foundSubfiles = [], []
        for something in os.listdir( tryFolderName ):
            somepath = os.path.join( givenFolderName, thisFolderName, something )
            if os.path.isdir( somepath ): foundSubfolders.append( something )
            elif os.path.isfile( somepath ):
                somethingUpper = something.upper()
                somethingUpperProper, somethingUpperExt = os.path.splitext( somethingUpper )
                ignore = False
                for ending in FILENAME_ENDINGS_TO_IGNORE:
                    if somethingUpper.endswith( ending): ignore=True; break
                if ignore: continue
                if not somethingUpperExt[1:] in EXTENSIONS_TO_IGNORE: # Compare without the first dot
                    foundSubfiles.append( something )
        #print( 'fsf', foundSubfiles )

        # See if there's an OSIS project here in this folder
        for thisFilename in sorted( foundSubfiles ):
            if strictCheck or BibleOrgSysGlobals.strictCheckingFlag:
                firstLines = BibleOrgSysGlobals.peekIntoFile( thisFilename, tryFolderName, numLines=2 )
                if not firstLines or len(firstLines)<2: continue
                if not firstLines[0].startswith( '<?xml version="1.0"' ) \
                and not firstLines[0].startswith( '\ufeff<?xml version="1.0"' ): # same but with BOM
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "OB (unexpected) first line was {!r} in {}".format( firstLines, thisFilename ) )
                    continue
                if not firstLines[1].startswith( '<osis ' ):
                    continue
            foundProjects.append( (tryFolderName, thisFilename,) )
            lastFilenameFound = thisFilename
            numFound += 1
    if numFound:
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "OSISXMLBibleFileCheck foundProjects", numFound, foundProjects )
        if numFound == 1 and (autoLoad or autoLoadBooks):
            if BibleOrgSysGlobals.debugFlag: assert( len(foundProjects) == 1 )
            ub = OSISXMLBible( foundProjects[0][0], foundProjects[0][1] ) # Folder and filename
            if autoLoadBooks: ub.load() # Load and process the file
            return ub
        return numFound
# end of OSISXMLBibleFileCheck



def clean( elementText, loadErrors=None, location=None, verseMilestone=None ):
    """
    Given some text from an XML element text or tail field (which might be None)
        return a stripped value and with internal CRLF characters replaced by spaces.

    If the text is None, returns None
    """
    if elementText is None: return None
    # else it's not None

    info = ''
    if location: info += ' at ' + location
    if verseMilestone: info += ' at ' + verseMilestone

    result = elementText
    while result.endswith('\n') or result.endswith('\r'): result = result[:-1] # Drop off trailing newlines (assumed to be irrelevant)
    if '  ' in result:
        errorMsg = t("clean: found multiple spaces in {!r}{}").format( result, info )
        logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
    if '\t' in result:
        errorMsg = t("clean: found tab in {!r}{}").format( result, info )
        logging.warning( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\t', ' ' )
    if '\n' in result or '\r' in result:
        errorMsg = t("clean: found CR or LF characters in {!r}{}").format( result, info )
        logging.error( errorMsg )
        if loadErrors is not None: loadErrors.append( errorMsg )
        result = result.replace( '\r\n', ' ' ).replace( '\n', ' ' ).replace( '\r', ' ' )
    while '  ' in result: result = result.replace( '  ', ' ' )
    return result
# end of clean



class OSISXMLBible( Bible ):
    """
    Class for reading, validating, and converting OSISXMLBible XML.
    This is only intended as a transitory class (used at start-up).
    The OSISXMLBible class has functions more generally useful.
    """
    filenameBase = "OSISXMLBible"
    XMLNameSpace = "{http://www.w3.org/XML/1998/namespace}"
    #OSISNameSpace = "{http://ebible.org/2003/OSIS/namespace}"
    OSISNameSpace = "{http://www.bibletechnologies.net/2003/OSIS/namespace}"
    treeTag = OSISNameSpace + "osis"
    textTag = OSISNameSpace + "osisText"
    headerTag = OSISNameSpace + "header"
    divTag = OSISNameSpace + 'div'


    def __init__( self, sourceFilepath, givenName=None, givenAbbreviation=None, encoding='utf-8' ):
        """
        Constructor: just sets up the OSIS Bible object.
        """
         # Setup and initialise the base class first
        Bible.__init__( self )
        self.objectNameString = "OSIS XML Bible object"
        self.objectTypeString = "OSIS"

        # Now we can set our object variables
        self.sourceFilepath, self.givenName, self.givenAbbreviation, self.encoding  = sourceFilepath, givenName, givenAbbreviation, encoding


        self.title = self.version = self.date = self.source = None
        self.tree = self.header = self.frontMatter = self.divs = self.divTypesString = None
        #self.bkData, self.USFMBooks = OrderedDict(), OrderedDict()
        self.lang = self.language = None


        # Do a preliminary check on the readability of our file(s)
        self.possibleFilenames = []
        if os.path.isdir( self.sourceFilepath ): # We've been given a folder -- see if we can find the files
            self.sourceFolder = self.sourceFilepath
            # There's no standard for OSIS xml file naming
            fileList = os.listdir( self.sourceFilepath )
            # First try looking for OSIS book names
            for filename in fileList:
                if filename.lower().endswith('.xml'):
                    self.sourceFilepath = os.path.join( self.sourceFolder, filename )
                    if BibleOrgSysGlobals.debugFlag: print( "Trying {}...".format( self.sourceFilepath ) )
                    if os.access( self.sourceFilepath, os.R_OK ): # we can read that file
                        self.possibleFilenames.append( filename )
        else: # it's presumably a file name
            self.sourceFolder = os.path.dirname( self.sourceFilepath )
            if not os.access( self.sourceFilepath, os.R_OK ):
                logging.critical( "OSISXMLBible: File {!r} is unreadable".format( self.sourceFilepath ) )
                return # No use continuing

        self.name, self.abbreviation = self.givenName, self.givenAbbreviation
    # end of OSISXMLBible.__init__


    def load( self ):
        """
        Loads the OSIS XML file or files.
        """
        loadErrors = []
        if self.possibleFilenames: # then we possibly have multiple files, probably one for each book
            for filename in self.possibleFilenames:
                pathname = os.path.join( self.sourceFolder, filename )
                self.__loadFile( pathname, loadErrors )
        elif os.path.isfile( self.sourceFilepath ): # most often we have all the Bible books in one file
            self.__loadFile( self.sourceFilepath, loadErrors )
        else:
            logging.critical( "OSISXMLBible: Didn't find anything to load at {!r}".format( self.sourceFilepath ) )
            loadErrors.append( _("OSISXMLBible: Didn't find anything to load at {!r}").format( self.sourceFilepath ) )
        if loadErrors:
            self.errorDictionary['Load Errors'] = loadErrors
            #if BibleOrgSysGlobals.debugFlag: print( "loadErrors", len(loadErrors), loadErrors ); halt
        self.doPostLoadProcessing()
    # end of OSISXMLBible.load


    def __loadFile( self, OSISFilepath, loadErrors ):
        """
        Load a single source XML file and remove the header from the tree.
        Also, extracts some useful elements from the header element.
        """
        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("Loading {}...").format( OSISFilepath ) )
        self.tree = ElementTree().parse( OSISFilepath )
        if BibleOrgSysGlobals.debugFlag: assert( len ( self.tree ) ) # Fail here if we didn't load anything at all

        # Find the main (osis) container
        if self.tree.tag == OSISXMLBible.treeTag:
            location = "OSIS file"
            BibleOrgSysGlobals.checkXMLNoText( self.tree, location, '4f6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( self.tree, location, '1wk8', loadErrors )
            # Process the attributes first
            self.schemaLocation = None
            for attrib,value in self.tree.items():
                if attrib.endswith("schemaLocation"):
                    self.schemaLocation = value
                else:
                    logging.warning( "fv6g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                    loadErrors.append( "Unprocessed {} attribute ({}) in {} (fv6g)".format( attrib, value, location ) )

            # Find the submain (osisText) container
            if len(self.tree)==1 and self.tree[0].tag == OSISXMLBible.textTag:
                sublocation = "osisText in " + location
                textElement = self.tree[0]
                BibleOrgSysGlobals.checkXMLNoText( textElement, sublocation, '3b5g', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( textElement, sublocation, '7h9k', loadErrors )
                # Process the attributes first
                self.osisIDWork = self.osisRefWork = canonical = None
                for attrib,value in textElement.items():
                    if attrib=='osisIDWork':
                        self.osisIDWork = value
                        if not self.name: self.name = value
                    elif attrib=='osisRefWork': self.osisRefWork = value
                    elif attrib=='canonical':
                        canonical = value
                        assert( canonical in ('true','false',) )
                    elif attrib==OSISXMLBible.XMLNameSpace+'lang': self.lang = value
                    else:
                        logging.warning( "gb2d Unprocessed {} attribute ({}) in {}".format( attrib, value, sublocation ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (gb2d)".format( attrib, value, sublocation ) )
                if self.osisRefWork:
                    if self.osisRefWork not in ('bible','Bible','defaultReferenceScheme',):
                        logging.warning( "New variety of osisRefWork: {!r}".format( self.osisRefWork ) )
                        loadErrors.append( "New variety of osisRefWork: {!r}".format( self.osisRefWork ) )
                if self.lang:
                    if self.lang in ('en','he',): # Only specifically recognise these ones so far (English, Hebrew)
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Language is {!r}".format( self.lang ) )
                    else:
                        logging.info( "Discovered an unknown {!r} language".format( self.lang ) )
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  osisIDWork is {!r}".format( self.osisIDWork ) )

                # Find (and move) the header container
                if textElement[0].tag == OSISXMLBible.headerTag:
                    self.header = textElement[0]
                    textElement.remove( self.header )
                    self.validateHeader( self.header, loadErrors )
                else:
                    logging.warning( "Missing header element (looking for {!r} tag)".format( OSISXMLBible.headerTag ) )
                    loadErrors.append( "Missing header element (looking for {!r} tag)".format( OSISXMLBible.headerTag ) )

                # Find (and move) the optional front matter (div) container
                if textElement[0].tag == OSISXMLBible.OSISNameSpace + 'div':
                    sub2location = "div of " + sublocation
                    # Process the attributes first
                    div0Type = div0OsisID = canonical = None
                    for attrib,value in textElement[0].items():
                        if attrib=='type': div0Type = value
                        elif attrib=='osisID': div0OsisID = value
                        elif attrib=='canonical':
                            assert( canonical is None )
                            canonical = value
                            assert( canonical in ('true','false') )
                        else:
                            logging.warning( "7j4d Unprocessed {} attribute ({}) in {}".format( attrib, value, sub2location ) )
                            loadErrors.append( "Unprocessed {} attribute ({}) in {} (7j4d)".format( attrib, value, sub2location ) )
                    if div0Type == 'front':
                        self.frontMatter = textElement[0]
                        textElement.remove( self.frontMatter )
                        self.validateFrontMatter( self.frontMatter )
                    else: logging.info( "No front matter division" )

                self.divs, self.divTypesString = [], None
                for element in textElement:
                    if element.tag == OSISXMLBible.divTag:
                        sub2location = "div in " + sublocation
                        BibleOrgSysGlobals.checkXMLNoText( element, sub2location, '3a2s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( element, sub2location, '4k8a', loadErrors )
                        divType = element.get( 'type' )
                        if divType is None:
                            logging.error( "Missing div type in OSIS file" )
                            loadErrors.append( "Missing div type in OSIS file" )
                        if divType != self.divTypesString:
                            if not self.divTypesString: self.divTypesString = divType
                            else: self.divTypesString = 'MixedTypes'
                        self.validateAndExtractMainDiv( element, loadErrors )
                        self.divs.append( element )
                    else:
                        logging.error( "Expected to find {!r} but got {!r}".format( OSISXMLBible.divTag, element.tag ) )
                        loadErrors.append( "Expected to find {!r} but got {!r}".format( OSISXMLBible.divTag, element.tag ) )
            else:
                logging.error( "Expected to find {!r} but got {!r}".format( OSISXMLBible.textTag, self.tree[0].tag ) )
                loadErrors.append( "Expected to find {!r} but got {!r}".format( OSISXMLBible.textTag, self.tree[0].tag ) )
        else:
            logging.error( "Expected to load {!r} but got {!r}".format( OSISXMLBible.treeTag, self.tree.tag ) )
            loadErrors.append( "Expected to load {!r} but got {!r}".format( OSISXMLBible.treeTag, self.tree.tag ) )
        if self.tree.tail is not None and self.tree.tail.strip():
            logging.error( "Unexpected {!r} tail data after {} element".format( self.tree.tail, self.tree.tag ) )
            loadErrors.append( "Unexpected {!r} tail data after {} element".format( self.tree.tail, self.tree.tag ) )
    # end of OSISXMLBible.loadFile


    def validateHeader( self, header, loadErrors ):
        """
        Check/validate the given OSIS header record.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS header...").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        headerlocation = "header"
        BibleOrgSysGlobals.checkXMLNoText( header, headerlocation, '2s90', loadErrors )
        BibleOrgSysGlobals.checkXMLNoAttributes( header, headerlocation, '4f6h', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( header, headerlocation, '0k6l', loadErrors )

        numWorks = 0
        for element in header:
            if element.tag == OSISXMLBible.OSISNameSpace+"revisionDesc":
                location = "revisionDesc of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, '2t5y', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '6hj8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, '3a1l', loadErrors )
                # Process the attributes first
                resp = None
                for attrib,value in element.items():
                    if attrib=="resp": resp = value
                    else:
                        logging.warning( "4j6a Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (4j6a)".format( attrib, value, location ) )

                # Now process the subelements
                for subelement in element:
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, '4f3f', loadErrors )
                    if len(subelement):
                        logging.error( "Unexpected {} subelements in subelement {} in {} revisionDesc".format( len(subelement), subelement.tag, osisWork ) )
                        loadErrors.append( "Unexpected {} subelements in subelement {} in {} revisionDesc".format( len(subelement), subelement.tag, osisWork ) )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'date':
                        sublocation = "date of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '9hj5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '6g3s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '4sd2', loadErrors )
                        date = subelement.text
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '4f4s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3c5g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '9k5a', loadErrors )
                        p = element.text
                    else:
                        logging.error( "6g4g Unprocessed {!r} sub-element ({}) in revisionDesc element".format( subelement.tag, subelement.text ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in revisionDesc element (6g4g)".format( subelement.tag, subelement.text ) )
                        if BibleOrgSysGlobals.debugFlag: halt
            elif element.tag == OSISXMLBible.OSISNameSpace+"work":
                location = "work of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, '5h9k', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '2s3d', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, '1d4f', loadErrors )
                # Process the attributes first
                osisWork = lang = None
                for attrib,value in element.items():
                    if attrib=="osisWork":
                        osisWork = value
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Have a {!r} work".format( osisWork ) )
                    elif attrib==OSISXMLBible.XMLNameSpace+"lang": lang = value
                    else:
                        logging.warning( "2k5s Unprocessed {} attribute ({}) in work element".format( attrib, value ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in work element (2k5s)".format( attrib, value ) )
                # Now process the subelements
                for subelement in element:
                    if len(subelement):
                        logging.error( "hf54 Unexpected {} subelements in subelement {} in {} work".format( len(subelement), subelement.tag, osisWork ) )
                        loadErrors.append( "Unexpected {} subelements in subelement {} in {} work (hf54)".format( len(subelement), subelement.tag, osisWork ) )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'title':
                        sublocation = "title of " + location
                        if 0: validateTitle( subelement, sublocation, verseMilestone )
                        else:
                            BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '0k5f', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '8k0k', loadErrors )
                            if not self.title: self.title = subelement.text # Take the first title
                            titleType = None
                            for attrib,value in subelement.items():
                                if attrib=='type': titleType = value
                                else:
                                    logging.warning( "8f83 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (8f83)".format( attrib, value, sublocation ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'version':
                        sublocation = "version of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, '3g1h', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '7h4f', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2j9z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '0k3d', loadErrors )
                        self.version = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "93d2 Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (93d2)".format( attrib, value, sublocation ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'date':
                        sublocation = "date of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '4x5h', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3f9j', loadErrors )
                        date = subelement.text
                        dateType = dateEvent = None
                        for attrib,value in subelement.items():
                            if attrib=='type': dateType = value
                            elif attrib=="event": dateEvent = value
                            else:
                                logging.warning( "2k4d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (2k4d)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.debugFlag: assert( dateType in (None,'Gregorian',) )
                        if BibleOrgSysGlobals.debugFlag: assert( dateEvent in (None,'eversion',) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"creator":
                        sublocation = "creator of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '9n3z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3n5z', loadErrors )
                        self.creator = subelement.text
                        creatorRole = creatorType = None
                        for attrib,value in subelement.items():
                            if attrib=="role": creatorRole = value
                            elif attrib=='type': creatorType = value
                            else:
                                logging.warning( "9f2d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (9f2d)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Creator (role={!r}{}) was {!r}".format( creatorRole, ", type={!r}".format(creatorType) if creatorType else '', self.creator ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"contributor":
                        sublocation = "contributor of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2u5z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3z4o', loadErrors )
                        self.contributor = subelement.text
                        contributorRole = None
                        for attrib,value in subelement.items():
                            if attrib=="role": contributorRole = value
                            else:
                                logging.warning( "1s5g Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (1s5g)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Contributor ({}) was {!r}".format( contributorRole, self.contributor ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"subject":
                        sublocation = "subject of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'frg3', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'ft4g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'c35g', loadErrors )
                        self.subject = subelement.text
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Subject was {!r}".format( self.subject ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"description":
                        sublocation = "description of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '4a7s', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1j6z', loadErrors )
                        self.description = subelement.text
                        descriptionType = descriptionSubType = resp = None
                        for attrib,value in subelement.items():
                            if attrib=='type': descriptionType = value
                            elif attrib=='subType': descriptionSubType = value
                            elif attrib=="resp": resp = value
                            else:
                                logging.warning( "6f3d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (6f3d)".format( attrib, value, sublocation ) )
                        if descriptionType: assert( descriptionType in ('usfm','x-english','x-lwc',) )
                        if descriptionType or self.description and BibleOrgSysGlobals.verbosityLevel > 2: print( "    Description{} is {!r}".format( " ({})".format(descriptionType) if descriptionType else '', self.description ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"format":
                        sublocation = "format of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8v3x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '5n3x', loadErrors )
                        self.format = subelement.text
                        formatType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': formatType = value
                            else:
                                logging.warning( "2f5s Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (2f5s)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.debugFlag: assert( formatType == 'x-MIME' )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Format ({}) is {!r}".format( formatType, self.format ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'type':
                        sublocation = "type of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8j8b', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3b4z', loadErrors )
                        self.type = subelement.text
                        typeType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': typeType = value
                            else:
                                logging.warning( "7j3f Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (7j3f)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.debugFlag: assert( typeType == 'OSIS' )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Type ({}) is {!r}".format( typeType, self.type ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"identifier":
                        sublocation = "identifier of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2x6e', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '5a2m', loadErrors )
                        identifier = subelement.text
                        identifierType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': identifierType = value
                            else:
                                logging.warning( "2d5g Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (2d5g)".format( attrib, value, sublocation ) )
                        #print( "id", repr(identifierType) )
                        if BibleOrgSysGlobals.debugFlag: assert( identifierType in ('OSIS','URL','x-ebible-id',) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Identifier ({}) is {!r}".format( identifierType, identifier ) )
                        #print( "Here vds1", repr(self.name), repr(self.abbreviation) )
                        if identifierType=='OSIS':
                            if not self.name: self.name = identifier
                            if identifier.startswith( 'Bible.' ) and not self.abbreviation:
                                self.abbreviation = identifier[6:]
                        self.identifier = identifier
                        #print( "Here vds2", repr(self.name), repr(self.abbreviation) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"source":
                        sublocation = "source of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '4gh7', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '6p3a', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1i8p', loadErrors )
                        self.source = subelement.text
                        sourceRole = None
                        for attrib,value in subelement.items():
                            if attrib=="role": sourceRole = value
                            else:
                                logging.warning( "6h7h Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (6h7h)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Source{} was {!r}".format( " ({})".format(sourceRole) if sourceRole else '', self.source ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"publisher":
                        sublocation = "publisher of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8n3x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3z7g', loadErrors )
                        self.publisher = subelement.text.replace( '&amp;', '&' )
                        publisherType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': publisherType = value
                            else:
                                logging.warning( "7g5g Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (7g5g)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Publisher {}is/was {!r}".format( '({}) '.format(publisherType) if publisherType else '', self.publisher ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"scope":
                        sublocation = "scope of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '3d4d', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '2g5z', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '1z4i', loadErrors )
                        self.scope = subelement.text
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Scope is {!r}".format( self.scope ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"coverage":
                        sublocation = "coverage of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '3d6g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3a6p', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '9l2p', loadErrors )
                        self.coverage = subelement.text
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Coverage is {!r}".format( self.coverage ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"refSystem":
                        sublocation = "refSystem of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2s4f', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '3mtp', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '3p65', loadErrors )
                        self.refSystem = subelement.text
                        if self.refSystem in ('Bible','Bible.KJV','Bible.NRSVA','Dict.Strongs','Dict.Robinsons','Dict.strongMorph',):
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Reference system is {!r}".format( self.refSystem ) )
                        else:
                            logging.info( "Discovered an unknown {!r} refSystem".format( self.refSystem ) )
                            loadErrors.append( "Discovered an unknown {!r} refSystem".format( self.refSystem ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"language":
                        sublocation = "language of " + location
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8n34', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '4v2n', loadErrors )
                        self.language = subelement.text
                        languageType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': languageType = value
                            else:
                                logging.warning( "6g4f Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (6g4f)".format( attrib, value, sublocation ) )
                        if languageType in ('SIL','IETF','x-ethnologue','x-in-english','x-vernacular',):
                            if ISOLanguages.isValidLanguageCode( self.language ):
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Language is: {}".format( ISOLanguages.getLanguageName( self.language ) ) )
                            else: print( "Discovered an unknown {!r} language".format( self.language ) )
                        else: print( "Discovered an unknown {!r} languageType".format( languageType ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"rights":
                        sublocation = "rights of " + location
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, '6v2x', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '9l5b', loadErrors )
                        self.rights = subelement.text
                        copyrightType = None
                        for attrib,value in subelement.items():
                            if attrib=='type': copyrightType = value
                            else:
                                logging.warning( "1s3d Unprocessed {!r} attribute ({}) in {}".format( attrib, value, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} (1s3d)".format( attrib, value, sublocation ) )
                        if BibleOrgSysGlobals.debugFlag: assert( copyrightType in (None,'x-copyright','x-license','x-license-url',) )
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Rights{} are/were {!r}".format( " ({})".format(copyrightType) if copyrightType else '', self.rights ) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"relation":
                        sublocation = "relation of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'g4h2', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, 'd2fd', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 's2fy', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'gh53', loadErrors )
                    else:
                        logging.error( "7h5g Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, location) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (7h5g)".format( subelement.tag, subelement.text, location) )
                        if BibleOrgSysGlobals.debugFlag: halt
                #if element.find('date') is not None: self.date = element.find('date').text
                #if element.find('title') is not None: self.title = element.find('title').text
                numWorks += 1
            elif element.tag == OSISXMLBible.OSISNameSpace+"workPrefix":
                location = "workPrefix of " + headerlocation
                BibleOrgSysGlobals.checkXMLNoText( header, location, 'f5h8', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( header, location, '6g4f', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( header, location, 'f2g7', loadErrors )
                # Process the attributes first
                workPrefixPath = workPrefixWork = None
                for attrib,value in element.items():
                    if attrib=="path": workPrefixPath = value
                    elif attrib=="osisWork": workPrefixWork = value
                    else:
                        logging.warning( "7yh4 Unprocessed {} attribute ({}) in workPrefix element".format( attrib, value ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in workPrefix element (7yh4)".format( attrib, value ) )
                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"revisionDesc":
                        sublocation = "revisionDesc of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation, 'c3t5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2w3e', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'm5o0', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'z2f8', loadErrors )
                        #self.something = subelement.text
                        for attrib,value in subelement.items():
                            logging.warning( "3h6r Unprocessed {!r} attribute ({}) in {} subelement of workPrefix element".format( attrib, value, subelement.tag ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} subelement of workPrefix element (3h6r)".format( attrib, value, subelement.tag ) )
                    else:
                        logging.error( "8h4g Unprocessed {!r} sub-element ({}) in workPrefix element".format( subelement.tag, subelement.text ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in workPrefix element (8h4g)".format( subelement.tag, subelement.text ) )
                        if BibleOrgSysGlobals.debugFlag: halt
            else:
                logging.error( "Expected to load {!r} but got {!r}".format( OSISXMLBible.OSISNameSpace+"work", element.tag ) )
                loadErrors.append( "Expected to load {!r} but got {!r}".format( OSISXMLBible.OSISNameSpace+"work", element.tag ) )
            if element.tail is not None and element.tail.strip():
                logging.error( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
                loadErrors.append( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
        if not numWorks:
            logging.warning( "OSIS header doesn't specify any work records." )
            loadErrors.append( "OSIS header doesn't specify any work records." )
    # end of OSISXMLBible.validateHeader


    def validateFrontMatter( self, frontMatter,loadErrors ):
        """
        Check/validate the given OSIS front matter (div) record.
        """
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS front matter...").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        frontMatterLocation = "frontMatter"
        BibleOrgSysGlobals.checkXMLNoText( frontMatter, frontMatterLocation, 'c3a2', loadErrors )
        BibleOrgSysGlobals.checkXMLNoTail( frontMatter, frontMatterLocation, 'm7s9', loadErrors )
        # Process the attributes first
        for attrib,value in frontMatter.items():
            if attrib=='type':
                pass # We've already processed this
            else:
                logging.warning( "98h4 Unprocessed {} attribute ({}) in {}".format( attrib, value, frontMatterLocation ) )
                loadErrors.append( "Unprocessed {} attribute ({}) in {} (98h4)".format( attrib, value, frontMatterLocation ) )

        for element in frontMatter:
            if element.tag == OSISXMLBible.OSISNameSpace+"titlePage":
                location = "titlePage of " + frontMatterLocation
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'k9l3', loadErrors )
                BibleOrgSysGlobals.checkXMLNoAttributes( element, location, '1w34', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'a3s4', loadErrors )
                # Process the attributes first
                for attrib,value in element.items():
                    if attrib=='type':
                        if BibleOrgSysGlobals.debugFlag: assert( value == 'front' ) # We've already processed this in the calling routine
                    else:
                        logging.warning( "3f5d Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (3f5d)".format( attrib, value, location ) )

                # Now process the subelements
                for subelement in element:
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, location, 'dv61', loadErrors )
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '5ygg', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, '8j54', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'h3x5', loadErrors )
                        p = element.text
                    else:
                        logging.error( "1dc5 Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (1dc5)".format( subelement.tag, subelement.text, location ) )
                        if BibleOrgSysGlobals.debugFlag: halt
            elif element.tag == OSISXMLBible.OSISNameSpace+'div':
                location = "div of " + frontMatterLocation
                BibleOrgSysGlobals.checkXMLNoText( element, location, 'b3f4', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location, 'd3s2', loadErrors )
                # Process the attributes first
                divType = None
                for attrib,value in element.items():
                    if attrib=='type': divType = value
                    else:
                        logging.warning( "7h4g Unprocessed {} attribute ({}) in {}".format( attrib, value, location ) )
                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (7h4g)".format( attrib, value, location ) )
                if BibleOrgSysGlobals.debugFlag: assert( divType == 'x-license' )

                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'title':
                        sublocation = "title of " + location
                        validateTitle( subelement, sublocation, verseMilestone )
                        #if 0:
                            #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '48j6', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation, 'l0l0', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'k8j8', loadErrors )
                            #date = subelement.text
                            #logging.warning( "sdh3 Not handled yet", subelement.text )
                            #loadErrors.append( "sdh3 Not handled yet", subelement.text )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        sublocation = "p of " + location
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation, '2de5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation, 'd4d4', loadErrors )
                        p = element.text
                        # Now process the subelements
                        for sub2element in subelement:
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sublocation, 's3s3', loadErrors )
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+"a":
                                sub2location = "a of " + sublocation
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location, 'j4h3', loadErrors )
                                aText, aTail = element.text, element.tail
                                # Process the attributes
                                href = None
                                for attrib,value in sub2element.items():
                                    if attrib=="href": href = value
                                    else:
                                        logging.warning( "7g4a Unprocessed {} attribute ({}) in {}".format( attrib, value, sub2location ) )
                                        loadErrors.append( "Unprocessed {} attribute ({}) in {} (7g4a)".format( attrib, value, sub2location ) )
                            else:
                                logging.error( "3d45 Unprocessed {!r} sub2-element ({}) in {}".format( sub2element.tag, sub2element.text, sublocation ) )
                                loadErrors.append( "Unprocessed {!r} sub2-element ({}) in {} (3d45)".format( sub2element.tag, sub2element.text, sublocation ) )
                    else:
                        logging.error( "034f Unprocessed {!r} sub-element ({}) in {}".format( subelement.tag, subelement.text, location ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (034f)".format( subelement.tag, subelement.text, location ) )
                        if BibleOrgSysGlobals.debugFlag: halt
            else:
                logging.error( "2sd4 Unprocessed {!r} sub-element ({}) in {}".format( element.tag, element.text, frontMatterLocation ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} (2sd4)".format( element.tag, element.text, frontMatterLocation ) )
                if BibleOrgSysGlobals.debugFlag: halt
            if element.tail is not None and element.tail.strip():
                logging.error( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
                loadErrors.append( "Unexpected {!r} tail data after {} element in header element".format( element.tail, element.tag ) )
    # end of OSISXMLBible.validateFrontMatter


    def validateAndExtractMainDiv( self, div, loadErrors ):
        """
        Check/validate and extract data from the given OSIS div record.
            This may be a book group, or directly into a book
        """

        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS main div...").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        haveEIDs = False
        self.haveBook = False


        def validateGroupTitle( element, locationDescription ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.
            """
            location = "validateGroupTitle: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoTail( element, location, 'c4vd', loadErrors )
            titleText = element.text
            titleType = titleSubType = titleShort = titleLevel = None
            for attrib,value in element.items():
                #if attrib=='type':
                    #titleType = value
                #elif attrib=='subType':
                    #titleSubType = value
                if attrib=='short':
                    titleShort = value
                #elif attrib=='level':
                    #titleLevel = value # Not used anywhere yet :(
                else:
                    logging.warning( "vdv3 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (vdv3)".format( attrib, value, location, verseMilestone ) )
            #if titleSubType: assert( titleSubType == 'x-preverse' )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at book group", 'js21', loadErrors )
            if BibleOrgSysGlobals.debugFlag: assert( titleText )
            if titleText:
                if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Got book group title", repr(titleText) )
                self.divisions[titleText] = []
        # end of OSISXMLBible.validateGroupTitle


        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=='type':
                mainDivType = value
                if mainDivOsisID and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}...").format( mainDivOsisID, mainDivType ) )
            elif attrib=="osisID":
                mainDivOsisID = value
                if mainDivType and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}...").format( mainDivOsisID, mainDivType ) )
            elif attrib=='canonical':
                mainDivCanonical = value
            else:
                logging.warning( "93f5 Unprocessed {!r} attribute ({}) in main div element".format( attrib, value ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in main div element (93f5)".format( attrib, value ) )
        if not mainDivType or not (mainDivOsisID or mainDivCanonical):
            logging.warning( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
            loadErrors.append( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )

        if mainDivType == 'bookGroup': # this is all the books lumped in together into one big div
            if BibleOrgSysGlobals.debugFlag: assert( mainDivCanonical == "true" )
            # We have to set BBB when we get a chapter reference
            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading a book group...") )
            self.haveBook = False
            for element in div:
                if element.tag == OSISXMLBible.OSISNameSpace+'title':
                    location = "title of {} div".format( mainDivType )
                    validateGroupTitle( element, location )
                elif element.tag == OSISXMLBible.OSISNameSpace+'div': # Assume it's a book
                    self.validateAndExtractBookDiv( element, loadErrors )
                else:
                    logging.error( "hfs6 Unprocessed {!r} sub-element ({}) in {} div".format( element.tag, element.text, mainDivType ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} div (hfs6)".format( element.tag, element.text, mainDivType ) )
                    if BibleOrgSysGlobals.debugFlag: halt
        elif mainDivType == 'book': # this is a single book (not in a group)
            self.validateAndExtractBookDiv( div, loadErrors )
        else:
            logging.critical( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            loadErrors.append( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            if BibleOrgSysGlobals.debugFlag:  halt
    # end of OSISXMLBible.validateAndExtractMainDiv


    def validateAndExtractBookDiv( self, div, loadErrors ):
        """
        Check/validate and extract data from the given OSIS div record.
            This should be a book division.
        """

        def validateChapterElement( element, chapterMilestone, verseMilestone, locationDescription ):
            """
            Check/validate and process a chapter element.

            Returns one of the following:
                OSIS chapter ID string for a startMilestone
                '' for an endMilestone
                'chapter' + chapter number string for a container
            """
            nonlocal BBB, USFMAbbreviation, USFMNumber #, bookResults, USFMResults
            #print( "validateChapterElement at {} with {} and {}".format( locationDescription, chapterMilestone, verseMilestone ) )
            location = "validateChapterElement: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 's2a8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'j9k7', loadErrors )
            OSISChapterID = sID = eID = chapterN = canonical = chapterTitle = None
            for attrib,value in element.items():
                if attrib=="osisID": OSISChapterID = value
                elif attrib=="sID": sID = value
                elif attrib=="eID": eID = value
                elif attrib=="n": chapterN = value
                elif attrib=='canonical': canonical = value
                elif attrib=="chapterTitle": chapterTitle = value
                else:
                    displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                    logging.warning( _("5f3d Unprocessed {!r} attribute ({}) in {} subelement of {}").format( attrib, value, displayTag, location ) )
                    loadErrors.append( _("Unprocessed {!r} attribute ({}) in {} subelement of {} (5f3d)").format( attrib, value, displayTag, location ) )
            if sID and not OSISChapterID:
                logging.error( _("Missing chapter ID attribute in {}: {}").format( location, element.items() ) )
                loadErrors.append( _("Missing chapter ID attribute in {}: {}").format( location, element.items() ) )

            if len(element)==0 and ( sID or eID or OSISChapterID): # it's a chapter milestone (no sub-elements)
                # No verse milestone should be open because verses can't cross chapter boundaries
                if verseMilestone:
                    if haveEIDs:
                        logging.error( _("Unexpected {} chapter milestone while {} verse milestone is still open at {}").format( element.items(), verseMilestone, location ) )
                        loadErrors.append( _("Unexpected {} chapter milestone while {} verse milestone is still open at {}").format( element.items(), verseMilestone, location ) )

                if OSISChapterID and sID and not eID:
                    chapterMilestone = sID
                    #if not chapterMilestone.count('.')==1: logging.warning( "{} chapter milestone seems wrong format for {} at {}".format( chapterMilestone, OSISChapterID, location ) )
                elif eID and not OSISChapterID and not sID:
                    if chapterMilestone and eID==chapterMilestone: chapterMilestone = ''
                    else:
                        logging.error( _("Chapter milestone {} end didn't match {} at {}").format( eID, chapterMilestone, location ) )
                        loadErrors.append( _("Chapter milestone {} end didn't match {} at {}").format( eID, chapterMilestone, location ) )
                elif OSISChapterID and not (sID or eID): # some OSIS formats use this
                    if BibleOrgSysGlobals.debugFlag: assert( canonical == "true" )
                    chapterMilestone = OSISChapterID
                else:
                    print( repr(OSISChapterID), repr(sID), repr(eID) )
                    logging.error( _("Unrecognized chapter milestone in {}: {} at {}").format( location, element.items(), location ) )
                    loadErrors.append( _("Unrecognized chapter milestone in {}: {} at {}").format( location, element.items(), location ) )

                if chapterMilestone: # Have a chapter milestone like Jas.1
                    if not OSISChapterID:
                        logging.error( "Missing chapter ID for {} at {}".format( chapterMilestone, location ) )
                        loadErrors.append( "Missing chapter ID for {} at {}".format( chapterMilestone, location ) )
                    else:
                        if not OSISChapterID.count('.')==1:
                            logging.error( "{} chapter ID seems wrong format for {} at {}".format( OSISChapterID, chapterMilestone, location ) )
                            loadErrors.append( "{} chapter ID seems wrong format for {} at {}".format( OSISChapterID, chapterMilestone, location ) )
                        bits = OSISChapterID.split( '.' )
                        if BibleOrgSysGlobals.debugFlag: assert( len(bits) == 2 )
                        cmBBB = None
                        try:
                            cmBBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromOSIS( bits[0] )
                        except KeyError:
                            logging.critical( _("{!r} is not a valid OSIS book identifier").format( bits[0] ) )
                            loadErrors.append( _("{!r} is not a valid OSIS book identifier").format( bits[0] ) )
                        if cmBBB and isinstance( cmBBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( "Multiple alternatives for OSIS {!r}: {} (Choosing the first one)".format( mainDivOsisID, cmBBB ) )
                            cmBBB = cmBBB[0]
                        if cmBBB and cmBBB != BBB: # We've started on a new book
                            #if BBB and ( len(bookResults)>20 or len(USFMResults)>20 ): # Save the previous book
                            print( "here", cmBBB, BBB, repr(chapterMilestone), len(self.thisBook._rawLines) )
                            if BBB and len(self.thisBook._rawLines) > 5: # Save the previous book
                                #print( verseMilestone )
                                if BibleOrgSysGlobals.verbosityLevel > 2: print( "Saving previous {}{} book into results...".format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
                                #print( mainDivOsisID, "results", BBB, bookResults[:10], "..." )
                                # Remove the last titles
                                #lastBookResult = bookResults.pop()
                                #if lastBookResult[0]!='sectionTitle':
                                    #lastBookResult = None
                                #lastUSFMResult = USFMResults.pop()
                                #if lastUSFMResult[0]!='s':
                                    #lastUSFMResult = None
                                lastLineTuple = self.thisBook._rawLines.pop()
                                if BibleOrgSysGlobals.debugFlag: assert( len(lastLineTuple) == 2 )
                                if lastLineTuple[0] != 's':
                                    self.thisBook._rawLines.append( lastLineTuple ) # No good -- put it back
                                    lastLineTuple = None
                                #if bookResults: self.bkData[BBB] = bookResults
                                #if USFMResults: self.USFMBooks[BBB] = USFMResults
                                self.saveBook( self.thisBook )
                                #bookResults, USFMResults = [], []
                                #if lastBookResult:
                                    #lastBookResultList = list( lastBookResult )
                                    #lastBookResultList[0] = 'mainTitle'
                                    #adjBookResult = tuple( lastBookResultList )
                                    ##print( lastBookResultList )
                                #if lastUSFMResult:
                                    #lastUSFMResultList = list( lastUSFMResult )
                                    #lastUSFMResultList[0] = 'mt1'
                                    ##print( lastUSFMResultList )
                                    #adjSFMResult = tuple( lastUSFMResultList )
                                if lastLineTuple:
                                    self.thisBook.addLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( ProgName, ProgVersion ) )
                                    self.thisBook.addLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
                                    self.thisBook.addLine( 'mt1', lastLineTuple[1] ) # Change from s to mt1
                                chapterMilestone = verseMilestone = ''
                                foundH = False
                            BBB = cmBBB[0] if isinstance( cmBBB, list) else cmBBB # It can be a list like: ['EZR', 'EZN']
                            #print( "23f4 BBB is", BBB )
                            USFMAbbreviation = BibleOrgSysGlobals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                            USFMNumber = BibleOrgSysGlobals.BibleBooksCodes.getUSFMNumber( BBB )
                            if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  It seems we have {}...").format( BBB ) )
                            self.thisBook = BibleBook( self, BBB )
                            self.thisBook.objectNameString = "OSIS XML Bible Book object"
                            self.thisBook.objectTypeString = "OSIS"
                            self.haveBook = True
                        self.thisBook.addLine( 'c', bits[1] )

                #print( "validateChapterElement returning milestone:", chapterMilestone )
                return chapterMilestone

            else: # not a milestone -- it's a chapter container
                bits = OSISChapterID.split('.')
                if BibleOrgSysGlobals.debugFlag: assert( len(bits)==2 and bits[1].isdigit() )
                #print( "validateChapterElement returning data:", 'chapterContainer.' + OSISChapterID )
                return 'chapterContainer.' + OSISChapterID
        # end of OSISXMLBible.validateChapterElement


        def validateVerseElement( element, verseMilestone, chapterMilestone, locationDescription ):
            """
            Check/validate and process a verse element.

            This currently handles three types of OSIS files:
                1/ Has verse start milestones and end milestones
                2/ Has verse start milestones but no end milestones
                3/ Verse elements are containers for the actual verse information

            Returns one of the following:
                OSIS verse ID string for a startMilestone
                '' for an endMilestone
                'verseContainer.' + verse number string for a container
                'verseContents#' + verse number string + '#' + verse contents for a verse contained within the <verse>...</verse> markers
            """
            nonlocal haveEIDs
            #print( "OSISXMLBible.validateVerseElement at {} with {!r} and {!r}".format( locationDescription, chapterMilestone, verseMilestone ) )
            location = "validateVerseElement: " + locationDescription
            verseText = element.text
            #print( "vT", verseText )
            #BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'x2f5', loadErrors )
            OSISVerseID = sID = eID = n = None
            for attrib,value in element.items():
                if attrib=="osisID": OSISVerseID = value
                elif attrib=="sID": sID = value
                elif attrib=="eID": eID = value
                elif attrib=="n": n = value
                else:
                    displayTag = element.tag[len(self.OSISNameSpace):] if element.tag.startswith(self.OSISNameSpace) else element.tag
                    logging.warning( "8jh6 Unprocessed {!r} attribute ({}) in {} subelement of {}".format( attrib, value, displayTag, location ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} subelement of {} (8jh6)".format( attrib, value, displayTag, location ) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( " validateVerseElement attributes: OSISVerseID = {!r} sID = {!r} eID = {!r} n = {!r}".format( OSISVerseID, sID, eID, n ) )
            if sID and eID:
                logging.critical( _("Invalid combined sID and eID verse attributes in {}: {}").format( location, element.items() ) )
            if sID and not OSISVerseID:
                logging.error( _("Missing verse attributes in {}: {}").format( location, element.items() ) )
                loadErrors.append( _("Missing verse attributes in {}: {}").format( location, element.items() ) )

            # See if this is a milestone or a verse container
            if len(element)==0 and ( sID or eID ): # it's a milestone (no sub-elements)
                if BibleOrgSysGlobals.debugFlag: assert( not verseText )
                if sID and OSISVerseID and not eID: # we have a start milestone
                    if verseMilestone: # but we already have an open milestone
                        if haveEIDs:
                            logging.error( "Got a {} verse milestone while {} is still open at {}".format( sID, verseMilestone, location ) )
                            loadErrors.append( "Got a {} verse milestone while {} is still open at {}".format( sID, verseMilestone, location ) )
                    verseMilestone = sID
                    #for char in (' ','-',):
                    #    if char in verseMilestone: # it contains a range like 'Mark.6.17 Mark.6.18' or 'Mark.6.17-Mark.6.18'
                    #        chunks = verseMilestone.split( char )
                    #        if BibleOrgSysGlobals.debugFlag: assert( len(chunks) == 2 )
                    #        verseMilestone = chunks[0] # Take the start of the range
                    #if not verseMilestone.count('.')==2: logging.error( "validateVerseElement: {} verse milestone seems wrong format for {}".format( verseMilestone, OSISVerseID ) )
                    vmBits, cmBits = verseMilestone.split( '.' ), chapterMilestone.split( '.' )
                    #print( "cv milestone stuff", repr(verseMilestone), repr(chapterMilestone), vmBits, cmBits )
                    if chapterMilestone.startswith( 'chapterContainer.' ): # The chapter is a container but the verse is a milestone!
                        if not verseMilestone.startswith( chapterMilestone[17:] ):
                            logging.error( "{!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                            loadErrors.append( "{!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                    elif vmBits[0:2] != cmBits[0:2]:
                        logging.error( "This {!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                        loadErrors.append( "This {!r} verse milestone seems wrong in {!r} chapter milestone at {}".format( verseMilestone, chapterMilestone, location ) )
                elif eID and not OSISVerseID and not sID: # we have an end milestone
                    #print( "here", repr(verseMilestone), repr(OSISVerseID), repr(sID), repr(eID) )
                    haveEIDs = True
                    if verseMilestone:
                        if eID==verseMilestone: pass # Good -- the end milestone matched the open start milestone
                        else:
                            logging.error( "{!r} verse milestone end didn't match last end milestone {!r} at {}".format( verseMilestone, eID, location ) )
                            loadErrors.append( "{!r} verse milestone end didn't match last end milestone {!r} at {}".format( verseMilestone, eID, location ) )
                    else:
                        logging.critical( "Have {!r} verse end milestone but no verse start milestone encountered at {}".format( eID, location ) )
                        loadErrors.append( "Have {!r} verse end milestone but no verse start milestone encountered at {}".format( eID, location ) )
                    return '' # end milestone closes any open milestone
                else:
                    logging.critical( "Unrecognized verse milestone in {}: {}".format( location, element.items() ) )
                    print( " ", verseMilestone ); halt
                    return '' # don't have any other way to handle this

                if verseMilestone: # have an open milestone
                    #print( "'"+verseMilestone+"'" )
                    if BibleOrgSysGlobals.debugFlag: assert( ' ' not in verseMilestone )
                    if '-' in verseMilestone: # Something like Jas.1.7-Jas.1.8
                        chunks = verseMilestone.split( '-' )
                        if len(chunks) != 2:
                            logging.error( "Shouldn't have multiple hyphens in verse milestone {!r}".format( verseMilestone ) )
                            loadErrors.append( "Shouldn't have multiple hyphens in verse milestone {!r}".format( verseMilestone ) )
                        bits1 = chunks[0].split( '.' )
                        if len(bits1) != 3:
                            logging.error( "Expected three components before hyphen in verse milestone {!r}".format( verseMilestone ) )
                            loadErrors.append( "Expected three components before hyphen in verse milestone {!r}".format( verseMilestone ) )
                        bits2 = chunks[1].split( '.' )
                        if len(bits2) != 3:
                            logging.error( "Expected three components after hyphen in verse milestone {!r}".format( verseMilestone ) )
                            loadErrors.append( "Expected three components after hyphen in verse milestone {!r}".format( verseMilestone ) )
                            bits2 = [bits1[0],bits1[1],'999'] # Try to do something intelligent
                        self.thisBook.addLine( 'v', bits1[2]+'-'+bits2[2] )
                    else: # no hyphen
                        bits = verseMilestone.split( '.' )
                        #print( "sdfssf", verseMilestone, bits )
                        if BibleOrgSysGlobals.debugFlag: assert( len(bits) >= 3 )
                        self.thisBook.addLine( 'v', bits[2]+' ' )
                    vTail = clean(element.tail) # Newlines and leading spaces are irrelevant to USFM formatting
                    if vTail: # This is the main text of the verse (follows the verse milestone)
                        self.thisBook.appendToLastLine( vTail )
                    return verseMilestone
                if BibleOrgSysGlobals.debugFlag: halt # Should not happen

            else: # not a milestone -- it's verse container
                BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 's2d4', loadErrors )
                bits = OSISVerseID.split('.')
                #print( "OSISXMLBible.validateVerseElement verse container bits", bits, 'vT', verseText )
                if BibleOrgSysGlobals.debugFlag: assert( len(bits)==3 and bits[1].isdigit() and bits[2].isdigit() )
                #print( "validateVerseElement: Have a verse container at", verseMilestone )
                if verseText.strip():
                    if self.source == "ftp://unboundftp.biola.edu/pub/albanian_utf8.zip": # Do some special handling
                        #print( "here", "&amp;quot;" in verseText, "&quot;" in verseText )
                        verseText = verseText.lstrip().replace('&quot;','"').replace('&lt;','<').replace('&gt;','>') # Fix some encoding issues
                        if "&" in verseText: print( "Still have ampersand in {!r}".format( verseText ) )
                    return 'verseContents#' + bits[2] + '#' + verseText
                else: # it's a container for subelements
                    return 'verseContainer.' + bits[2]

            if BibleOrgSysGlobals.debugFlag: halt # Should never reach this point in the code
        # end of OSISXMLBible.validateVerseElement


        def validateDivineName( element, locationDescription, verseMilestone ):
            """
            """
            location = "validateDivineName: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '3f7h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'v4g7', loadErrors )
            divineName, trailingText = element.text, element.tail
            self.thisBook.appendToLastLine( '\\nd {}\\nd*'.format( clean(divineName) ) )
            if trailingText and trailingText.strip(): self.thisBook.appendToLastLine( clean(trailingText) )
        # end of validateDivineName


        def validateProperName( element, locationDescription, verseMilestone ):
            """
            """
            location = "validateProperName: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'hsd8', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'ks91', loadErrors )
            divineName, trailingText = element.text, element.tail
            self.thisBook.appendToLastLine( '\\pn {}\\pn*'.format( clean(divineName) ) )
            if trailingText and trailingText.strip(): self.thisBook.appendToLastLine( clean(trailingText) )
        # end of validateProperName


        def validateSigned( element, locationDescription, verseMilestone ):
            """
            """
            location = "validateSigned: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '9i6h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'vd62', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'fc3v3', loadErrors )
            signedName = subelement.text
            if BibleOrgSysGlobals.debugFlag and subelement.tail: halt
            self.thisBook.appendToLastLine( '\\sg {}\\sg*'.format( clean(signedName) ) )
        # end of validateSigned


        def validateHighlight( element, locationDescription, verseMilestone ):
            """
            Also handles the tail.

            Might be nested like:
                <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
            Nesting doesn't currently work here.
            """
            location = "validateHighlight: " + locationDescription
            #BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'gb5g', loadErrors )
            highlightedText, highlightedTail = element.text, element.tail
            #if not highlightedText: print( "validateHighlight", repr(highlightedText), repr(highlightedTail), repr(location), repr(verseMilestone) )
            #if BibleOrgSysGlobals.debugFlag: assert( highlightedText ) # No text if nested!
            highlightType = None
            for attrib,value in element.items():
                if attrib=='type':
                    highlightType = value
                else:
                    logging.warning( "7kj3 Unprocessed {!r} attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} element of {} at {} (7kj3)".format( attrib, value, element.tag, location, verseMilestone ) )
            if highlightType == 'italic': marker = 'it'
            elif highlightType == 'bold': marker = 'bd'
            elif highlightType == 'emphasis': marker = 'em'
            elif highlightType == 'small-caps': marker = 'sc'
            elif highlightType == 'super': marker = 'ord'
            elif BibleOrgSysGlobals.debugFlag:
                print( 'highlightX', highlightType, locationDescription, verseMilestone )
                if BibleOrgSysGlobals.debugFlag: halt
            self.thisBook.appendToLastLine( '\\{} {}\\{}*'.format( marker, clean(highlightedText), marker ) )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "hi of " + locationDescription
                    validateHighlight( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "note of " + locationDescription
                    validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                else:
                    logging.error( "bdhj Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (bdhj)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            if highlightedTail and highlightedTail.strip(): self.thisBook.appendToLastLine( clean(highlightedTail) )
        # end of validateHighlight


        def validateSEG( element, locationDescription, verseMilestone ):
            """
            Also handles the tail.

            Might be nested like:
                <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
            Nesting doesn't currently work here.
            """
            location = 'validateSEG: ' + locationDescription
            SegText, SegTail = element.text, element.tail
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'mjd4', loadErrors )
            # Process the attributes
            theType = None
            for attrib,value in element.items():
                if attrib=='type': theType = value
                else:
                    logging.warning( "lj06 Unprocessed {!r} attribute ({}) in {} -element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} -element of {} at {} (lj06)".format( attrib, value, element.tag, location, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            if debuggingThisModule: print( "khf8", "Have", location, repr(element.text), repr(theType) )
            if theType:
                if theType=='verseNumber': marker = 'fv'
                elif theType=='keyword': marker = 'fk'
                elif theType=='otPassage': marker = 'qt'
                elif theType=='section': marker = 'section' # invented -- used below
                elif BibleOrgSysGlobals.debugFlag: print(  theType, location, verseMilestone ); halt
            else: # What marker do we need ???
                marker = 'fv'
            if marker == 'section': # We don't have marker for this
                self.thisBook.appendToLastLine( ' ' + clean(SegText) + ' ' )
            else: self.thisBook.appendToLastLine( '\\{} {}'.format( marker, clean(SegText) ) )
            if SegTail:
                self.thisBook.appendToLastLine( '\\f* {}'.format( clean(SegTail) ) ) # Do we need that space?
        # end of validateSEG


        def validateRDG( element, locationDescription, verseMilestone ):
            """
            Also handles the tail.

            Might be nested like:
                <hi type="bold"><hi type="italic">buk</hi></hi> tainoraun ämän
            Nesting doesn't currently work here.
            """
            location = 'validateRDG: ' + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '2s5h', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c54b', loadErrors )
            # Process the attributes first
            readingType = None
            for attrib,value in element.items():
                if attrib=='type':
                    readingType = value
                    #print( readingType )
                    if BibleOrgSysGlobals.debugFlag: assert( readingType == 'x-qere' )
                else:
                    logging.warning( "2s3d Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (2s3d)".format( attrib, value, element.tag, location, verseMilestone ) )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'w': # cross-references
                    sublocation = "validateRDG: w of rdg of " + locationDescription
                    #print( "  Have", sublocation, "6n83" )
                    rdgW = subelement.text
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 's2vb', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '5b3f', loadErrors )
                    # Process the attributes
                    lemma = None
                    for attrib,value in subelement.items():
                        if attrib=="lemma": lemma = value
                        else:
                            logging.warning( "6b8m Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (6b8m)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    self.thisBook.addLine( 'rdgW', rdgW )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg': # cross-references
                    sublocation = "validateRDG: seg of rdg of " + locationDescription
                    validateSEG( subelement, sublocation, verseMilestone )
                    #if 0:
                        ##print( "  Have", sublocation, "6n83" )
                        #rdgSeg = subelement.text
                        #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'fyg5', loadErrors )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 's2db', loadErrors )
                        ## Process the attributes
                        #theType = None
                        #for attrib,value in subelement.items():
                            #if attrib=='type': theType = value
                            #else:
                                #logging.warning( "k6g3 Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (k6g3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #self.thisBook.addLine( 'rdgSeg', rdgSeg )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "validateRDG: hi of rdg of " + locationDescription
                    validateHighlight( subelement, sublocation, verseMilestone )
                else:
                    logging.error( "3dxm Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (3dxm)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
        # end of validateRDG


        def validateLB( element, locationDescription, verseMilestone ):
            """
            """
            location = "validateLB: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'cf4g', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, '5t3x', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'sn52', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '3c5f', loadErrors )
            self.thisBook.addLine( 'm', '' )
        # end of OSISXMLBible.validateLB


        def validateWord( element, location, verseMilestone ):
            """
            Handle a 'w' element and submit a string (which may include embedded Strongs' numbers).
            """
            sublocation = "validateWord: w of " + location
            word = clean( element.text, loadErrors, sublocation, verseMilestone )
            if word: self.thisBook.appendToLastLine( word )
            # Process the attributes
            lemma = morph = wType = src = gloss = None
            for attrib,value in element.items():
                if attrib=='lemma': lemma = value
                elif attrib=='morph': morph = value
                elif attrib=='type': wType = value
                elif attrib=='src': src = value
                elif attrib=='gloss': gloss = value
                else:
                    logging.warning( "2h6k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (2h6k)".format( attrib, value, sublocation, verseMilestone ) )
            if wType and BibleOrgSysGlobals.debugFlag: assert( wType.startswith( 'x-split-' ) ) # Followed by a number 1-10 or more
            if lemma and lemma.startswith('strong:'):
                if len(lemma)>7:
                    lemma = lemma[7:]
                    if lemma:
                        self.thisBook.appendToLastLine( '\\str {}\\str*'.format( lemma ) )
                        lemma = None # we've used it
            elif gloss and gloss.startswith('s:'):
                if len(gloss)>2:
                    gloss = gloss[2:]
                    if gloss:
                        self.thisBook.appendToLastLine( '\\str {}\\str*'.format( gloss ) )
                        gloss = None # we've used it
            if lemma or morph or wType or src or gloss:
                logging.warning( "Losing lemma or morph or wType or src or gloss here at {} from {}".format( verseMilestone, BibleOrgSysGlobals.elementStr(element) ) )
                loadErrors.append( "Losing lemma or morph or wType or src or gloss here at {}".format( verseMilestone ) )
            assert( len(element) <= 1 )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    validateDivineName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                    validateSEG( subelement, sublocation, verseMilestone )
                else:
                    logging.error( "8k3s Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (8k3s)".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            trailingPunctuation = clean( element.tail, loadErrors, sublocation, verseMilestone )
            if trailingPunctuation: self.thisBook.appendToLastLine( trailingPunctuation )
            #combinedWord = word + trailingPunctuation
            #return combinedWord
        # end of validateWord


        def validateTransChange( element, location, verseMilestone ):
            """
            Handle a transChange element and return a string.
            """
            sublocation = "validateTransChange: transChange of " + location
            # Process the attributes
            transchangeType = None
            for attrib,value in element.items():
                if attrib=='type': transchangeType = value
                else:
                    logging.warning( "8q1k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (8q1k)".format( attrib, value, sublocation, verseMilestone ) )
            if BibleOrgSysGlobals.debugFlag: assert( transchangeType in ('added',) )
            tcText = clean(element.text) if element.text else ''
            self.thisBook.appendToLastLine( '\\add {}'.format( tcText ) )
            # Now process the subelements
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                    sublocation = "validateTransChange: w of transChange of " + location
                    validateWord( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateTransChange: divineName of transChange of " + location
                    validateDivineName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                    sublocation = "validateTransChange: name of transChange of " + location
                    validateProperName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "validateTransChange: note of transChange of " + location
                    validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                    sublocation = "validateTransChange: seg of transChange of " + location
                    validateSEG( subelement, sublocation, verseMilestone )
                else:
                    logging.error( "dfv3 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (dfv3)".format( subelement.tag, subelement.text, sublocation, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            tcTail = clean(element.tail) if element.tail else ''
            self.thisBook.appendToLastLine( '\\add*{}'.format( tcTail ) )
        # end of validateTransChange


        def validateCrossReferenceOrFootnote( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a cross-reference or footnote.
            """
            #print( "validateCrossReferenceOrFootnote at", locationDescription, verseMilestone )
            #print( "element tag={!r} text={!r} tail={!r} attr={} ch={}".format( element.tag, element.text, element.tail, element.items(), element ) )
            location = "validateCrossReferenceOrFootnote: " + locationDescription
            noteType = noteN = noteOsisRef = noteOsisID = notePlacement = noteResp = None
            openFieldname = None
            for attrib,value in element.items():
                if attrib=='type': noteType = value # cross-reference or empty for a footnote
                elif attrib=="n": noteN = value
                elif attrib=='osisRef': noteOsisRef = value
                elif attrib=="osisID": noteOsisID = value
                elif attrib=="placement": notePlacement = value
                elif attrib=="resp": noteResp = value
                else:
                    logging.warning( "2s4d Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (2s4d)".format( attrib, value, element.tag, location, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            #print( notePlacement )
            if notePlacement and BibleOrgSysGlobals.debugFlag: assert( notePlacement in ('foot','inline',) )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                print( "  Note attributes: noteType={!r} noteN={!r} noteOsisRef={!r} noteOsisID={!r} at {}".format( noteType, noteN, noteOsisRef, noteOsisID, verseMilestone ) )
            guessed = False
            if not noteType: # easier to handle later if we decide what it is now
                if not element.items(): # it's just a note with NO ATTRIBUTES at all
                    noteType = 'footnote'
                else: # we have some attributes
                    noteType = 'footnote' if noteN else 'crossReference'
                guessed = True
            #assert( noteType and noteN )
            if noteType == 'crossReference':
                #print( "  noteType =", noteType, "noteN =", noteN, "notePlacement =", notePlacement )
                if BibleOrgSysGlobals.debugFlag:
                    if notePlacement: assert( notePlacement == 'inline' )
                if not noteN: noteN = '-'
                self.thisBook.appendToLastLine( '\\x {}'.format( noteN ) )
                openFieldname = 'x'
            elif noteType == 'footnote':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if BibleOrgSysGlobals.debugFlag: assert( not notePlacement )
                if not noteN: noteN = '+'
                self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
                openFieldname = 'f'
            elif noteType == 'study':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if BibleOrgSysGlobals.debugFlag: assert( not notePlacement )
                if not noteN: noteN = '+'
                self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
                openFieldname = 'f'
                #print( "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); halt
            elif noteType == 'translation':
                #print( "  noteType =", noteType, "noteN =", noteN, "notePlacement =", notePlacement )
                if BibleOrgSysGlobals.debugFlag:
                    if notePlacement: assert( notePlacement == 'foot' )
                if not noteN: noteN = '+'
                self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
                openFieldname = 'f'
                #print( "study note1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); halt
            elif noteType == 'variant':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if BibleOrgSysGlobals.debugFlag: assert( not notePlacement )
                # What do we do here ???? XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
                #if not noteN: noteN = '+'
                self.thisBook.addLine( 'var', noteN )
            elif noteType == 'x-index':
                #print( "  noteType =", noteType, "noteN =", noteN )
                if BibleOrgSysGlobals.debugFlag: assert( notePlacement in ('inline',) )
                if not noteN: noteN = '~'
                self.thisBook.addLine( 'ix', noteN )
            elif noteType == 'x-strongsMarkup':
                #print( "  noteType =", noteType, "noteN =", noteN, repr(notePlacement) )
                if BibleOrgSysGlobals.debugFlag: assert( notePlacement is None )
                if not noteN: noteN = '+ '
                self.thisBook.appendToLastLine( '\\f {} '.format( noteN ) )
                openFieldname = 'f'
            else:
                print( "note1", noteType )
                if BibleOrgSysGlobals.debugFlag: halt
            noteText = clean( element.text, loadErrors, location, verseMilestone )
            #if not noteText or noteText.isspace(): # Maybe we can infer the anchor reference
            #    if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
            #        noteText = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
            #    else: noteText = ''
            if noteText and not noteText.isspace(): # In some OSIS files, this is the anchor reference (in others, that's put in the tail of an enclosed reference subelement)
                #print( "vm", verseMilestone, repr(noteText) ); halt
                #if verseMilestone.startswith( 'Matt.6'): halt
                #print( "  noteType = {}, noteText = {!r}".format( noteType, noteText ) )
                if noteType == 'crossReference': # This could be something like '1:6:' or '1:8: a'
                    self.thisBook.appendToLastLine( '\\xt {}'.format( clean(noteText) ) )
                elif noteType == 'footnote': # This could be something like '4:3 In Greek: some note.' or it could just be random text
                    #print( "  noteType =", noteType, "noteText =", noteText )
                    if BibleOrgSysGlobals.debugFlag: assert( noteText )
                    if ':' in noteText and noteText[0].isdigit(): # Let's roughly assume that it starts with a chapter:verse reference
                        bits = noteText.split( None, 1 )
                        if BibleOrgSysGlobals.debugFlag: assert( len(bits) == 2 )
                        sourceText, footnoteText = bits
                        if BibleOrgSysGlobals.debugFlag: assert( sourceText and footnoteText )
                        #print( "  footnoteSource = {!r}, sourceText = {!r}".format( footnoteSource, sourceText ) )
                        if not sourceText[-1] == ' ': sourceText += ' '
                        self.thisBook.appendToLastLine( '\\fr {}'.format( sourceText ) )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( footnoteText )  )
                    else: # Let's assume it's a simple note
                        self.thisBook.appendToLastLine( '\\ft {}'.format( noteText ) )
                elif noteType == 'study':
                    #print( "Need to handle study note properly here" ) # ................. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    self.thisBook.appendToLastLine( '\\ft {}'.format( clean(noteText) ) )
                    #print( "study note dg32", location, "Type =", noteType, "N =", repr(noteN), "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
                elif noteType == 'translation':
                    #print( "Need to handle translation note properly here" ) # ................. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    self.thisBook.appendToLastLine( '\\ft {}'.format( clean(noteText) ) )
                    #print( "translation note fgd1", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement )
                elif noteType == 'x-index':
                    #print( "Need to handle index note properly here" ) # ................. xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                    self.thisBook.addLine( 'ix~', noteText )
                elif noteType == 'x-strongsMarkup':
                    self.thisBook.appendToLastLine( '\\ft {}'.format( noteText ) )
                else:
                    print( "note2", noteType )
                    if BibleOrgSysGlobals.debugFlag: halt
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'reference': # cross-references
                    sublocation = "validateCrossReferenceOrFootnote: reference of " + locationDescription
                    #print( "  Have", sublocation, "7h3f" )
                    referenceText = subelement.text.strip()
                    referenceTail = (subelement.tail if subelement.tail is not None else '').strip()
                    referenceOsisRef = referenceType = None
                    for attrib,value in subelement.items():
                        if attrib=='osisRef': referenceOsisRef = value
                        elif attrib=='type': referenceType = value
                        else:
                            logging.warning( "1sc5 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (1sc5)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.debugFlag: halt
                    #print( "  reference attributes: noteType = {}, referenceText = {!r}, referenceOsisRef = {!r}, referenceType = {!r}, referenceTail = {!r}". \
                    #                        format( noteType, referenceText, referenceOsisRef, referenceType, referenceTail ) )
                    if not referenceType and referenceText: # Maybe we can infer the anchor reference
                        if verseMilestone and verseMilestone.count('.')==2: # Something like Gen.1.3
                            #print( 'vm', verseMilestone )
                            #print( 'ror', referenceOsisRef )
                            anchor = verseMilestone.split('.',1)[1] # Just get the verse reference like "1.3"
                            #referenceType = 'source' # so it works below for cross-references
                            #print( 'rt', referenceText )
                            if noteType=='crossReference':
                                #assert( not noteText and not referenceTail )
                                if noteText and not noteText.isspace():
                                    logging.error( "What do we do here with the note at {}".format( verseMilestone ) )
                                    loadErrors.append( "What do we do here with the note at {}".format( verseMilestone ) )
                                self.thisBook.appendToLastLine( '\\xo {}'.format( anchor ) )
                            elif noteType=='footnote':
                                self.thisBook.addLine( 'v~', anchor ) # There's no USFM for this
                            else:
                                print( sublocation, verseMilestone, noteType, referenceType, referenceText )
                                if BibleOrgSysGlobals.debugFlag: halt
                    if noteType=='crossReference' and referenceType=='source':
                        #assert( not noteText and not referenceTail )
                        if BibleOrgSysGlobals.debugFlag: assert( not noteText or noteText.isspace() )
                        self.thisBook.appendToLastLine( '\\xt {}'.format( referenceText ) )
                    elif noteType=='crossReference' and not referenceType and referenceOsisRef is not None:
                        if 0 and USFMResults and USFMResults[-1][0]=='xt': # Combine multiple cross-references into one xt field
                            self.thisBook.appendToLastLine( '\\xt {}'.format( USFMResults.pop()[1]+referenceText+referenceTail ) )
                        else:
                            self.thisBook.appendToLastLine( '\\xt {}'.format( clean(referenceText+referenceTail) ) )
                    elif noteType=='footnote' and referenceType=='source':
                        if BibleOrgSysGlobals.debugFlag: assert( referenceText and not noteText )
                        if not referenceText[-1] == ' ': referenceText += ' '
                        self.thisBook.appendToLastLine( '\\fr {}'.format( clean(referenceText) ) )
                        if BibleOrgSysGlobals.debugFlag: assert( referenceTail )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( clean(referenceTail) ) )
                    elif noteType=='study' and referenceType=='source': # This bit needs fixing up properly ................................xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                        #print( "rT={!r} nT={!r} rTail={!r}".format( referenceText, noteText, referenceTail ) )
                        if BibleOrgSysGlobals.debugFlag: assert( referenceText and not noteText.strip() )
                        if not referenceText[-1] == ' ': referenceText += ' '
                        if referenceTail: self.thisBook.addLine( 'st', referenceTail )
                        #else: logging.warning( "How come there's no tail? rT={!r} nT={!r} rTail={!r}".format( referenceText, noteText, referenceTail ) )
                        #print( "study note3", location, "Type =", noteType, "N =", noteN, "Ref =", noteOsisRef, "ID =", noteOsisID, "p =", notePlacement ); halt
                    elif noteType=='translation' and referenceType=='source': # This bit needs fixing up properly ................................xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
                        if BibleOrgSysGlobals.debugFlag and debuggingThisModule:
                            print( "rT={!r} nT={!r} rTail={!r}".format( referenceText, noteText, referenceTail ) )
                            assert( referenceText and not noteText )
                        if not referenceText[-1] == ' ': referenceText += ' '
                        self.thisBook.appendToLastLine( '\\fr {}'.format( referenceText ) )
                        if referenceTail and referenceTail.strip(): self.thisBook.appendToLastLine( '\\ft {}'.format( clean(referenceTail) ) )
                    else:
                        logging.critical( "Don't know how to handle notetype={!r} and referenceType={!r} yet".format( noteType, referenceType ) )
                        loadErrors.append( "Don't know how to handle notetype={!r} and referenceType={!r} yet".format( noteType, referenceType ) )
                    for sub2element in subelement: # Can have nested references in some (horrible) OSIS files)
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'reference': # cross-references
                            sub2location = "validateCrossReferenceOrFootnote: reference of reference of " + locationDescription
                            #print( "  Have", sub2location, "w3r5" )
                            BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7', loadErrors )
                            subreferenceText = sub2element.text
                            if BibleOrgSysGlobals.debugFlag: assert( noteType == 'crossReference' )
                            self.thisBook.appendToLastLine( '\\xo {}'.format( subreferenceText ) )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'foreign':
                            sub2location = "validateCrossReferenceOrFootnote: foreign of reference of " + locationDescription
                            BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '67t4', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '6hnm', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'x3b7', loadErrors )
                            subreferenceText = sub2element.text
                            self.thisBook.appendToLastLine( '\\tl {}\\tl*'.format( clean(subreferenceText) ) )
                        else:
                            logging.error( "7h45 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (7h45)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"q":
                    sublocation = "validateCrossReferenceOrFootnote: q of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'n56d', loadErrors )
                    qWho = qReferenceType = None
                    for attrib,value in subelement.items():
                        if attrib=='who': qWho = value
                        elif attrib=='type': qReferenceType = value
                        else:
                            logging.warning( "3d4r Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (3d4r)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.debugFlag: halt
                        if qReferenceType: assert( qReferenceType in ('x-footnote',) )
                    #print( "noteType", repr(noteType) )
                    if BibleOrgSysGlobals.debugFlag: assert( noteType in ('footnote','translation',) )
                    qText, qTail = subelement.text.strip(), subelement.tail
                    if BibleOrgSysGlobals.debugFlag: assert( qText )
                    self.thisBook.appendToLastLine( '\\fq {}'.format( qText ) )
                    if qTail and qTail.strip():
                        #print( 'qTail', repr(qTail) )
                        self.thisBook.appendToLastLine( '\\ft {}'.format( clean(qTail) ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'catchWord':
                    sublocation = "validateCrossReferenceOrFootnote: catchWord of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '2w43', loadErrors )
                    catchWordText, catchWordTail = subelement.text, subelement.tail
                    if noteType == 'footnote':
                        self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                        for sub2element in subelement: # Can have nested catchWords in some (horrible) OSIS files)
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'catchWord': #
                                sub2location = "validateCrossReferenceOrFootnote: catchWord of catchWord of " + locationDescription
                                #print( "  Have", sub2location, "j2f6" )
                                BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '2d4r', loadErrors )
                                BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '23c6', loadErrors )
                                BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, 'c456n', loadErrors )
                                subCatchWordText = sub2element.text
                                if BibleOrgSysGlobals.debugFlag: assert( noteType == 'footnote' )
                                self.thisBook.appendToLastLine( '\\fq {}'.format( subCatchWordText ) )
                            else:
                                logging.error( "8j6g Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (8j6g)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                if BibleOrgSysGlobals.debugFlag: halt
                    elif noteType == 'translation':
                        self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh36', loadErrors )
                    elif noteType == 'variant':
                        self.thisBook.appendToLastLine( '\\fq {}'.format( clean(catchWordText) ) )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fh36', loadErrors )
                    else:
                        print( noteType, "not handled" )
                        if BibleOrgSysGlobals.debugFlag: halt
                    if catchWordTail:
                        self.thisBook.appendToLastLine( '\\fq* {}'.format( clean(catchWordTail) ) ) # Do we need the space
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "validateCrossReferenceOrFootnote: hi of " + locationDescription
                    validateHighlight( subelement, sublocation, verseMilestone ) # Also handles the tail
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'rdg':
                    sublocation = "validateCrossReferenceOrFootnote: rdg of " + locationDescription
                    validateRDG( subelement, sublocation, verseMilestone ) # Also handles the tail
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateCrossReferenceOrFootnote: divineName of " + locationDescription
                    validateDivineName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                    sublocation = "validateCrossReferenceOrFootnote: name of " + locationDescription
                    validateProperName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg': # cross-references
                    sublocation = "validateCrossReferenceOrFootnote: seg of " + locationDescription
                    validateSEG( subelement, sublocation, verseMilestone ) # Also handles the tail
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "validateCrossReferenceOrFootnote: note of " + locationDescription
                    noteText = subelement.text
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vw24', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'plq2', loadErrors )
                    # Process the attributes
                    notePlacement = noteOsisRef = noteOsisID = noteType = None
                    for attrib,value in subelement.items():
                        if attrib=='type': noteType = value
                        elif attrib=='placement': notePlacement = value
                        elif attrib=='osisRef': noteOsisRef = value
                        elif attrib=="osisID": noteOsisID = value
                        else:
                            logging.warning( "f5j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (f5j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    logging.error( "odf3 Unprocessed note: {} {} {} {} {}".format( repr(noteText), repr(noteType), repr(notePlacement), repr(noteOsisRef), repr(noteOsisID) ) )
                    loadErrors.append( "Unprocessed note: {} {} {} {} {} (odf3)".format( repr(noteText), repr(noteType), repr(notePlacement), repr(noteOsisRef), repr(noteOsisID) ) )
                    if BibleOrgSysGlobals.debugFlag: halt
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                    sublocation = "validateCrossReferenceOrFootnote: transChange of " + locationDescription
                    validateTransChange( subelement, sublocation, verseMilestone ) # Also handles the tail
                    #if 0:
                        #tcText = subelement.text
                        #if BibleOrgSysGlobals.debugFlag: assert( tcText )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'fvd8', loadErrors )
                        ## Process the attributes
                        #tcType = None
                        #for attrib,value in subelement.items():
                            #if attrib=='type': tcType = value
                            #else:
                                #logging.warning( "f0j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (f0j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #if BibleOrgSysGlobals.debugFlag: assert( tcType == "added" )
                        #tcTail = subelement.tail if subelement.tail else ''
                        #self.thisBook.appendToLastLine( '\\add {}\\add*{}'.format( tcText, tcTail ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                    sublocation = "validateCrossReferenceOrFootnote: foreign of " + locationDescription
                    fText = subelement.text
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'cbf6', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'cbf4', loadErrors )
                    # Process the attributes
                    fN = None
                    for attrib,value in subelement.items():
                        if attrib=='n': fN = value
                        else:
                            logging.warning( "h0j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (h0j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    logging.error( "Unused {!r} foreign field at {}".format( fText, sublocation+" at "+verseMilestone ) )
                    loadErrors.append( "Unused {!r} foreign field at {}".format( fText, sublocation+" at "+verseMilestone ) )
                else:
                    logging.error( "1d54 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (1d54)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if debuggingThisModule: halt
            if openFieldname: self.thisBook.appendToLastLine( '\\{}*'.format( openFieldname ) )
            noteTail = clean( element.tail, loadErrors, location, verseMilestone )
            if noteTail: self.thisBook.appendToLastLine( noteTail )
        # end of OSISXMLBible.validateCrossReferenceOrFootnote


        def validateLG( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible lg field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #print( "validateLG at {} at {}".format( location, verseMilestone ) )
            location = "validateLG: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6v', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'vdj4', loadErrors )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'l':
                    sublocation = "validateLG l of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d56g', loadErrors )
                    level3 = None
                    for attrib,value in subelement.items():
                        if attrib=='level':
                            level3 = value
                        else:
                            logging.warning( "2xc4 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (2xc4)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    if not level3:
                        #print( "level3 problem", verseMilestone, lText, subelement.items() )
                        logging.warning( "No level attribute specified in {} at {}".format( sublocation, verseMilestone ) )
                        loadErrors.append( "No level attribute specified in {} at {}".format( sublocation, verseMilestone ) )
                        level3 = '1' # Dunno what we have here ???
                    if BibleOrgSysGlobals.debugFlag: assert( level3 in ('1','2','3','4',) )
                    self.thisBook.addLine( 'q'+level3, '' if subelement.text is None else clean(subelement.text) )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            sub2location = "validateLG: verse of l of " + locationDescription
                            verseMilestone = validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                            sub2location = "validateLG: note of l of " + locationDescription
                            validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                            sub2location = "validateLG: divineName of l of " + locationDescription
                            validateDivineName( sub2element, sub2location, verseMilestone )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                            sub2location = "validateLG: hi of l of " + locationDescription
                            validateHighlight( sub2element, sub2location, verseMilestone ) # Also handles the tail
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                            sub2location = "validateLG: w of l of " + locationDescription
                            validateWord( sub2element, sub2location, verseMilestone )
                            #print( "wordStuff", repr(wordStuff), sublocation, verseMilestone, BibleOrgSysGlobals.elementStr(subelement) )
                            #if wordStuff: self.thisBook.appendToLastLine( wordStuff )
                        else:
                            logging.error( "4j12 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (4j12)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateLG divineName of " + locationDescription
                    validateDivineName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateLG verse of " + locationDescription
                    verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                else:
                    logging.error( "q2b6 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (q2b6)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            if element.tail: # and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                self.thisBook.addLine( 'm', clean(element.tail) )
            return verseMilestone
        # end of OSISXMLBible.validateLG


        def validateList( element, locationDescription, verseMilestone, level=None ):
            """
            Check/validate and process a OSIS Bible list field, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            #print( "validateList for {} at {} at {}".format( self.name, locationDescription, verseMilestone ) )
            if level is None: level = 1
            location = "validateList: " + locationDescription

            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '2dx3', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '2c5b', loadErrors )
            canonical = None
            for attrib,value in element.items():
                if attrib== 'canonical':
                    canonical = value
                    assert( canonical == 'false' )
                else:
                    logging.warning( "h2f5 Unprocessed {!r} attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} element of {} at {} (h2f5)".format( attrib, value, element.tag, location, verseMilestone ) )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+"item":
                    sublocation = "item of " + location
                    itemText = subelement.text
                    #print( "itemText", repr(itemText) )
                    if chapterMilestone: marker = 'li' + str(level)
                    else: marker = 'io' + str(level) # No chapter so we're in the introduction
                    if itemText and itemText.strip(): self.thisBook.addLine( marker, clean(itemText) )
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'xf52', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'ad36', loadErrors )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            sub2location = "verse of " + sublocation
                            verseMilestone = validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location )
                            #verseTail = sub3element.tail
                            #print( "verseTail", repr(verseTail) )
                            #BibleOrgSysGlobals.checkXMLNoText( sub3element, sub3location+" at "+verseMilestone, 'cvf4', loadErrors )
                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'sdyg', loadErrors )
                            #osisID = verseSID = verseEID = verseN = None
                            #for attrib,value in sub3element.items():
                                #if attrib=='osisID':
                                    #osisID = value
                                #elif attrib=='sID':
                                    #verseSID = value
                                #elif attrib=='eID':
                                    #verseEID = value
                                #elif attrib=='n':
                                    #verseN = value
                                #else: logging.warning( "fghb Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                            #if osisID: assert( verseSID and verseN and not verseEID )
                            #elif verseEID: assert( not verseSID and not verseN )
                            #print( "verseStuff", repr(osisID), repr(verseSID), repr(verseN), repr(verseEID) )
                            ##self.thisBook.addLine( 'r~', referenceText+referenceTail )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                            sub2location = "note of " + sublocation
                            validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                            sub2location = "hi of " + sublocation
                            validateHighlight( sub2element, sub2location, verseMilestone )
                        elif sub2element.tag == OSISXMLBible.OSISNameSpace+'list':
                            sub2location = "list of " + sublocation
                            verseMilestone = validateList( sub2element, sub2location, verseMilestone, level+1 )
                        else:
                            logging.error( "f153 Unprocessed {!r} sub3element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (f153)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                else:
                    logging.error( "s154 Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (s154)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            return verseMilestone

            ##print( 'list', divType, subDivType )
            #BibleOrgSysGlobals.checkXMLNoText( sub2element, sub2location+" at "+verseMilestone, '3x6g', loadErrors )
            #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '8j4g' )
            #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, '7tgf' )
            #for sub3element in sub2element:
                #if sub3element.tag == OSISXMLBible.OSISNameSpace+"item":
                    #sub3location = "item of " + sub2location
                    #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '3d8n' )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '4g7g' )
                    #item = sub3element.text
                    #if item and item.strip():
                        ##print( subDivType )
                        #if subDivType == 'outline':
                            #self.thisBook.addLine( 'io1', item.strip() )
                        #elif subDivType == 'section':
                            #self.thisBook.addLine( 'io1', item.strip() )
                        #elif BibleOrgSysGlobals.debugFlag: halt
                    #for sub4element in sub3element:
                        #if sub4element.tag == OSISXMLBible.OSISNameSpace+'list':
                            #sub4location = "list of " + sub3location
                            #BibleOrgSysGlobals.checkXMLNoText( sub4element, sub4location+" at "+verseMilestone, '5g3d' )
                            #BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '4w5x' )
                            #BibleOrgSysGlobals.checkXMLNoAttributes( sub4element, sub4location+" at "+verseMilestone, '3d45' )
                            #for sub5element in sub4element:
                                #if sub5element.tag == OSISXMLBible.OSISNameSpace+"item":
                                    #sub5location = "item of " + sub4location
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub5element, sub5location+" at "+verseMilestone, '4c5t' )
                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub5element, sub5location+" at "+verseMilestone, '2sd1' )
                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub5element, sub5location+" at "+verseMilestone, '8j7n' )
                                    #subItem = sub5element.text
                                    #if subItem:
                                        #if subDivType == 'outline':
                                            #self.thisBook.addLine( 'io2', clean(subItem) )
                                        #elif subDivType == 'section':
                                            #self.thisBook.addLine( 'io2', clean(subItem) )
                                        #elif BibleOrgSysGlobals.debugFlag: print( subDivType ); halt
                                #else: logging.error( "3kt6 Unprocessed {!r} sub5element ({}) in {} at {}".format( sub5element.tag, sub5element.text, sub4location, verseMilestone ) )
                        #elif sub4element.tag == OSISXMLBible.OSISNameSpace+'verse':
                            #sub4location = "list of " + sub3location
                            #validateVerseElement( sub4element, verseMilestone, chapterMilestone, sub4location )
                        #else: logging.error( "2h4s Unprocessed {!r} sub4element ({}) in {} at {}".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                #else: logging.error( "8k4j Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
        # end of OSISXMLBible.validateList


        def validateTitle( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.
            """
            location = "validateTitle: " + locationDescription
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'c4vd', loadErrors )
            titleText = clean( element.text, loadErrors, location, verseMilestone )
            titleType = titleSubType = titleShort = titleLevel = titleCanonicalFlag = None
            for attrib,value in element.items():
                if attrib=='type':
                    titleType = value
                elif attrib=='subType':
                    titleSubType = value
                elif attrib=='short':
                    titleShort = value
                elif attrib=='level':
                    titleLevel = value
                elif attrib=='canonical':
                    titleCanonicalFlag = value
                    assert( titleCanonicalFlag in ('true','false',) )
                else:
                    logging.warning( "4b8e Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (4b8e)".format( attrib, value, location, verseMilestone ) )
            #print( 'vdq2', repr(titleType), repr(titleSubType), repr(titleText), titleLevel, titleCanonicalFlag )
            if BibleOrgSysGlobals.debugFlag:
                if titleType: assert( titleType in ('main','chapter','psalm','scope','sub','parallel','acrostic',) )
                if titleSubType: assert( titleSubType == 'x-preverse' )
            if chapterMilestone:
                #print( 'title', verseMilestone, repr(titleText), repr(titleType), repr(titleSubType), repr(titleShort), repr(titleLevel) )
                if titleText:
                    if not titleType and not titleShort and self.language=='ksw': # it's a Karen alternate chapter number
                        self.thisBook.addLine( 'cp', titleText )
                    elif titleType == 'parallel':
                        self.thisBook.addLine( 'sr', titleText )
                    elif titleCanonicalFlag=='true':
                        assert( titleType == 'psalm' )
                        self.thisBook.addLine( 'd', titleText )
                    else: # let's guess that it's a section heading
                        if debuggingThisModule:
                            print( "title assumed to be section heading", verseMilestone, repr(titleText), repr(titleType), repr(titleSubType), repr(titleShort), repr(titleLevel) )
                        sfm = 's'
                        if titleLevel:
                            assert( titleLevel in ('1','2','3') )
                            sfm += titleLevel
                        self.thisBook.addLine( sfm, titleText )
            else: # must be in the introduction if it's before all chapter milestones
            #if self.haveBook:
                #assert( titleText )
                if titleText:
                    #print( 'title', repr(titleText) )
                    self.thisBook.addLine( 'imt', titleText ) # Could it also be 'is'?
            #else: # Must be a book group title
                #BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at book group", 'vcw5', loadErrors )
                #if BibleOrgSysGlobals.debugFlag: assert( titleText )
                #if titleText:
                    #if BibleOrgSysGlobals.verbosityLevel > 2: print( "    Got book group title", repr(titleText) )
                    #self.divisions[titleText] = []
                    ##self.thisBook.addLine( 'bgt', titleText ) # Could it also be 'is'?
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+'title': # section reference(s)
                    sublocation = "validateTitle: title of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '21d5', loadErrors )
                    titleText = clean( subelement.text, loadErrors, sublocation, verseMilestone )
                    # Handle attributes
                    titleType = titleLevel = None
                    for attrib,value in subelement.items():
                        if attrib== 'type': titleType = value
                        elif attrib== 'level': titleLevel = value
                        else:
                            logging.warning( "56v3 Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (56v3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    if titleText:
                        #print( repr(mainDivType), repr(titleType), repr(titleLevel), repr(chapterMilestone) )
                        if chapterMilestone: marker = 'sr'
                        else: marker = 'mt{}'.format( titleLevel if titleLevel else '' )
                        self.thisBook.addLine( marker, titleText )
                    for sub2element in subelement:
                        if sub2element.tag == OSISXMLBible.OSISNameSpace+'reference':
                            sub2location = "reference of " + sublocation
                            BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'f5g2', loadErrors )
                            referenceText = clean( sub2element.text, loadErrors, sub2location, verseMilestone )
                            referenceTail = clean( sub2element.tail, loadErrors, sub2location, verseMilestone )
                            referenceOsisRef = None
                            for attrib,value in sub2element.items():
                                if attrib=='osisRef':
                                    referenceOsisRef = value
                                else:
                                    logging.warning( "89n5 Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub2element.tag, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub3element of {} at {} (89n5)".format( attrib, value, sub2element.tag, sublocation, verseMilestone ) )
                            if BibleOrgSysGlobals.debugFlag:
                                print( 'here bd02', repr(referenceText), repr(referenceOsisRef), repr(referenceTail) )
                            self.thisBook.addLine( 'r', referenceText+referenceTail )
                        else:
                            logging.error( "2d6h Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (2d6h)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "validateTitle: hi of " + locationDescription
                    validateHighlight( subelement, sublocation, verseMilestone ) # Also handles the tail
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "validateTitle: note of " + locationDescription
                    validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'w': # Probably a canonical Psalm title
                    sublocation = "validateTitle: w of " + locationDescription
                    validateWord( subelement, sublocation, verseMilestone )
                    #if 0:
                        #word = subelement.text if subelement.text else ''
                        ## Handle attributes
                        #lemma = morph = None
                        #for attrib,value in subelement.items():
                            #if attrib=="lemma": lemma = value
                            #elif attrib=="morph": morph = value
                            #else:
                                #logging.warning( "dv42 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (dv42)".format( attrib, value, sublocation, verseMilestone ) )
                        #if lemma and lemma.startswith('strong:'):
                            #word += "\\str {}\\str*".format( lemma[7:] )
                            #lemma = None # we've used it
                        #if lemma or morph:
                            #if BibleOrgSysGlobals.debugFlag: logging.info( "Losing lemma or morph here at {}".format( verseMilestone ) )
                            #loadErrors.append( "Losing lemma or morph here at {}".format( verseMilestone ) )
                        ## Handle sub-elements
                        #for sub2element in subelement:
                            #if sub2element.tag == OSISXMLBible.OSISNameSpace+'xyz':
                                #sub2location = "divineName of " + sublocation
                                #BibleOrgSysGlobals.checkXMLNoAttributes( sub2element, sub2location+" at "+verseMilestone, 'fbf3', loadErrors )
                                #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, 'kje3', loadErrors )
                                #if BibleOrgSysGlobals.debugFlag: assert( sub2element.text )
                                ##print( "Here scw2", repr(sub2element.text) )
                                #word += "\\nd {}\\nd*".format( sub2element.text )
                                #if sub2element.tail: word += sub2element.tail
                            #else:
                                #logging.error( "kd92 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (kd92)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                #if BibleOrgSysGlobals.debugFlag: halt
                        #if subelement.tail: word += subelement.tail
                        #self.thisBook.appendToLastLine( word )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'abbr':
                    sublocation = "validateTitle: abbr of " + locationDescription
                    abbrText = subelement.text
                    abbrTail = subelement.tail
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'gd56', loadErrors )
                    # Handle attributes
                    abbrExpansion = None
                    for attrib,value in subelement.items():
                        if attrib== 'expansion': abbrExpansion = value
                        else:
                            logging.warning( "vsy3 Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (vsy3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    #self.thisBook.appendToLastLine( '{}\\abbr {}\\abbr*{}'.format( abbrText, abbrExpansion, abbrTail ) )
                    logging.warning( "Unused {}={} abbr field at {}".format( repr(abbrText), repr(abbrExpansion), sublocation+" at "+verseMilestone ) )
                    loadErrors.append( "Unused {}={} abbr field at {}".format( repr(abbrText), repr(abbrExpansion), sublocation+" at "+verseMilestone ) )
                    self.thisBook.appendToLastLine( '{}{}'.format( abbrText, abbrTail ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+"transChange":
                    sublocation = "validateTitle: transChange of " + locationDescription
                    validateTransChange( subelement, sublocation, verseMilestone ) # Also handles the tail
                    #if 0:
                        #tcText = subelement.text
                        #if BibleOrgSysGlobals.debugFlag: assert( tcText )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'gvd8', loadErrors )
                        ## Process the attributes
                        #tcType = None
                        #for attrib,value in subelement.items():
                            #if attrib=='type': tcType = value
                            #else:
                                #logging.warning( "g0j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (g0j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #if BibleOrgSysGlobals.debugFlag: assert( tcType == "added" )
                        #tcTail = subelement.tail if subelement.tail else ''
                        #self.thisBook.appendToLastLine( '\\add {}\\add*{}'.format( tcText, tcTail ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                    sublocation = "validateTitle: foreign of " + locationDescription
                    fText = subelement.text
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'cbf6', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'cbf4', loadErrors )
                    # Process the attributes
                    fN = None
                    for attrib,value in subelement.items():
                        if attrib=='n': fN = value
                        else:
                            logging.warning( "h0j3 Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (h0j3)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    logging.error( "Unused {!r} foreign field at {}".format( fText, sublocation+" at "+verseMilestone ) )
                    loadErrors.append( "Unused {!r} foreign field at {}".format( fText, sublocation+" at "+verseMilestone ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'reference':
                    sublocation = "validateTitle: reference of " + locationDescription
                    rText = subelement.text
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'ld10', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'js12', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'jsv2', loadErrors )
                    logging.error( "Unused {!r} reference field at {}".format( rText, sublocation+" at "+verseMilestone ) )
                    loadErrors.append( "Unused {!r} reference field at {}".format( rText, sublocation+" at "+verseMilestone ) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateTitle: verse of " + locationDescription
                    verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                    sublocation = "validateTitle: verse of " + locationDescription
                    validateSEG( subelement, sublocation, verseMilestone )
                else:
                    logging.error( "jkd7 Unprocessed {!r} subelement ({}) in {} at {}".format( subelement.tag, subelement.text, locationDescription, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} subelement ({}) in {} at {} (jkd7)".format( subelement.tag, subelement.text, locationDescription, verseMilestone ) )
                    if BibleOrgSysGlobals.debugFlag: halt
            #titleTail = clean( element.tail, loadErrors, location, verseMilestone )
        # end of OSISXMLBible.validateTitle


        def validateParagraph( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible paragraph, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            nonlocal chapterMilestone
            #print( "validateParagraph at {} at {}".format( locationDescription, verseMilestone ) )
            location = "validateParagraph: " + locationDescription
            paragraphType = canonical = None
            for attrib,value in element.items():
                if attrib=='type':
                    paragraphType = value
                elif attrib=='canonical':
                    canonical = value
                    assert( canonical in ('true','false',) )
                else:
                    logging.warning( "6g3f Unprocessed {!r} attribute ({}) in {} element of {} at {}".format( attrib, value, element.tag, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} element of {} at {} (6g3f)".format( attrib, value, element.tag, location, verseMilestone ) )
            paragraphCode = None
            if paragraphType:
                if BibleOrgSysGlobals.debugFlag:
                    assert( paragraphType.startswith( 'x-') )
                    if paragraphType not in  ('x-center','x-iex','x-mi','x-pc','x-ph','x-pm','x-pmr','x-qa','x-qc','x-qm','x-qr','x-sr',): print( paragraphType )
                    if debuggingThisModule:
                        assert( paragraphType in ('x-center','x-iex','x-mi','x-pc','x-ph','x-pm','x-pmr','x-qa','x-qc','x-qm','x-qr','x-sr',) )
                paragraphCode = paragraphType[2:]
            justFinishedLG = False
            if not element.text: # A new paragraph starting
                pContents = None
            else: # A new paragraph in the middle of a verse, e.g., James 3:5b
                pContents = clean( element.text )
                #if pContents.isspace(): pContents = None # Ignore newlines and blank lines in the xml file
            if paragraphCode in USFM_BIBLE_PARAGRAPH_MARKERS:
                self.thisBook.addLine( paragraphCode, '' if pContents is None else pContents )
            elif chapterMilestone:
                self.thisBook.addLine( 'p', '' if pContents is None else pContents )
            else: # Must be in the introduction
                self.thisBook.addLine( 'ip', '' if pContents is None else pContents )
            for subelement in element:
                if subelement.tag == OSISXMLBible.OSISNameSpace+"chapter": # A chapter break within a paragraph (relatively rare)
                    sublocation = "validateParagraph: chapter of " + locationDescription
                    chapterMilestone = validateChapterElement( subelement, chapterMilestone, verseMilestone, sublocation )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                    sublocation = "validateParagraph: verse of " + locationDescription
                    if justFinishedLG: # Have a verse straight after a LG (without an intervening p)
                        self.thisBook.addLine( 'm', '' )
                        #print( "Added m" )
                    verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                    sublocation = "validateParagraph: note of " + locationDescription
                    validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'lg':
                    sublocation = "validateParagraph: lg of " + locationDescription
                    verseMilestone = validateLG( subelement, sublocation, verseMilestone )
                    #if 0:
                        #BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, '3ch6', loadErrors )
                        ##lgText = subelement.text
                        #lgTail = subelement.tail
                        #for attrib,value in subelement.items():
                            #if attrib=='type':
                                #halt
                            #elif attrib=="n":
                                #halt
                            #elif attrib=='osisRef':
                                #halt
                            #elif attrib=="osisID":
                                #halt
                            #else:
                                #logging.warning( "1s5g Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (1s5g)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #for sub2element in subelement:
                            #if sub2element.tag == OSISXMLBible.OSISNameSpace+'l':
                                #sub2location = "l of " + sublocation
                                #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4vw3', loadErrors )
                                #lText = sub2element.text
                                #level3 = None
                                #for attrib,value in sub2element.items():
                                    #if attrib=='level':
                                        #level3 = value
                                    #else:
                                        #logging.warning( "9d3k Unprocessed {!r} attribute ({}) in {} sub-element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                        #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub-element of {} at {} (9d3k)".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                #if not level3:
                                    ##print( "level3 problem", verseMilestone, lText, sub2element.items() )
                                    #logging.warning( "validateParagraph: No level attribute specified in {} at {}".format( sub2location, verseMilestone ) )
                                    #loadErrors.append( "validateParagraph: No level attribute specified in {} at {}".format( sub2location, verseMilestone ) )
                                    #level3 = '1' # Dunno what we have here ???
                                #if BibleOrgSysGlobals.debugFlag: assert( level3 in ('1','2','3',) )
                                #self.thisBook.addLine( 'q'+level3, lText )
                                #for sub3element in sub2element:
                                    #if sub3element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                        #sub3location = "verse of " + sub2location
                                        #verseMilestone = validateVerseElement( sub3element, verseMilestone, chapterMilestone, sub3location )
                                    #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'note':
                                        #sub3location = "note of " + sub2location
                                        #validateCrossReferenceOrFootnote( sub3element, sub3location, verseMilestone )
                                        #noteTail = sub3element.tail
                                        #if noteTail: # This is the main text of the verse (follows the inserted note)
                                            #bookResults.append( ('lverse+', noteTail,) )
                                            #adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                            #if adjNoteTail: USFMResults.append( ('v~',adjNoteTail,) )
                                    #else:
                                        #logging.error( "32df Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                        #loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (32df)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            #else:
                                #logging.error( "5g1e Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (5g1e)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        #if lgTail and lgTail!='\n': # This is the main text of the verse (outside of the quotation indents)
                            #self.thisBook.addLine( 'm', lgTail )
                    justFinishedLG = True
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'reference':
                    sublocation = "validateParagraph: reference of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'vbs4', loadErrors )
                    reference = subelement.text
                    theType = None
                    for attrib,value in subelement.items():
                        if attrib=='type':
                            theType = value
                        else:
                            logging.warning( "4f5f Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (4f5f)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                    if theType:
                        if theType == 'x-bookName':
                            self.thisBook.appendToLastLine( '\\bk {}\\bk*'.format( clean(reference) ) )
                        elif BibleOrgSysGlobals.debugFlag: print( theType ); halt
                    pTail = subelement.tail
                    if pTail and pTail.strip(): # Just ignore XML spacing characters
                        self.thisBook.appendToLastLine( clean(pTail) )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'hi':
                    sublocation = "validateParagraph: hi of " + locationDescription
                    validateHighlight( subelement, sublocation, verseMilestone ) # Also handles the tail
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'lb':
                    sublocation = "validateParagraph: lb of " + locationDescription
                    validateLB( subelement, sublocation, verseMilestone )
                    justFinishedLG = False
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                    sublocation = "validateParagraph: w of " + locationDescription
                    validateWord( subelement, sublocation, verseMilestone )
                    #print( "wordStuff", repr(wordStuff), sublocation, verseMilestone, BibleOrgSysGlobals.elementStr(subelement) )
                    #if wordStuff: self.thisBook.appendToLastLine( wordStuff )
                    #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '3s5f', loadErrors )
                    #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'f3v5', loadErrors )
                    #word, trailingPunctuation = subelement.text, subelement.tail
                    #if trailingPunctuation is None: trailingPunctuation = ''
                    #combined = word + trailingPunctuation
                    #self.thisBook.addLine( 'w~', combined )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'signed':
                    sublocation = "validateParagraph: signed of " + locationDescription
                    validateSigned( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                    sublocation = "validateParagraph: divineName of " + locationDescription
                    validateDivineName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'name':
                    sublocation = "validateParagraph: name of " + locationDescription
                    validateProperName( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'seg':
                    sublocation = "validateParagraph: seg of " + locationDescription
                    validateSEG( subelement, sublocation, verseMilestone )
                    #if 0:
                        #segText, segTail = subelement.text, subelement.tail
                        #segType = None
                        #for attrib,value in subelement.items():
                            #if attrib=='type': segType = value
                            #else:
                                #logging.error( "bsh2 Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {}".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2-element of {} at {} (bsh2)".format( attrib, value, subelement.tag, sublocation, verseMilestone ) )
                        #if segType:
                            #if segType == 'otPassage':
                                #marker = 'qt'
                            #elif segType == 'keyword':
                                #marker = 'k'
                            #elif BibleOrgSysGlobals.debugFlag: print( segType ); halt
                        #else: marker = 'k' # what should it be ???
                        #self.thisBook.appendToLastLine( '\\{} {}'.format( marker, clean(segText) ) )
                        #for sub2element in subelement:
                            #if sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                                #sub2location = "validateParagraph: divineName of seg of  " + locationDescription
                                #validateDivineName( sub2element, sub2location, verseMilestone )
                            #else:
                                #logging.error( "f352 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                #loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (f352)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                        #self.thisBook.appendToLastLine( '\\{}*'.format( marker ) )
                        #if segTail and segTail.strip(): self.thisBook.appendToLastLine( clean(segTail) )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'transChange':
                    sublocation = "validateParagraph: transChange of " + locationDescription
                    validateTransChange( subelement, sublocation, verseMilestone )
                elif subelement.tag == OSISXMLBible.OSISNameSpace+'foreign':
                    sublocation = "validateParagraph: foreign of reference of " + locationDescription
                    BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'kd02', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'kls2', loadErrors )
                    BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, 'ks10', loadErrors )
                    subreferenceText = subelement.text
                    self.thisBook.appendToLastLine( '\\tl {}\\tl*'.format( clean(subreferenceText) ) )
                else:
                    logging.error( "3kj6 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (3kj6)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                    if debuggingThisModule: halt
            if element.tail and not element.tail.isspace(): # Just ignore XML spacing characters
                self.thisBook.appendToLastLine( element.tail )
            return verseMilestone
        # end of OSISXMLBible.validateParagraph


        def validateTable( element, locationDescription, verseMilestone ):
            """
            Check/validate and process a OSIS Bible table, including all subfields.

            Returns a possibly updated verseMilestone.
            """
            location = "validateTable: " + locationDescription
            self.thisBook.addLine( 'tr', ' ' )
            BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, 'kd20', loadErrors )
            BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'kd21', loadErrors )
            BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'ks20', loadErrors )
            BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, 'so20', loadErrors )
            tableTail = clean(element.tail, loadErrors, location, verseMilestone )
            if tableTail: self.thisBook.appendToLastLine( tableTail )
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: halt
            return verseMilestone
        # end of OSISXMLBible.validateTable



        # Main code for validateAndExtractBookDiv
        if BibleOrgSysGlobals.verbosityLevel > 3: print( _("Loading {}OSIS book div...").format( self.abbreviation+' ' if self.abbreviation else '' ) )
        haveEIDs = False
        self.haveBook = False

        # Process the div attributes first
        mainDivType = mainDivOsisID = mainDivCanonical = None
        BBB = USFMAbbreviation = USFMNumber = ''
        for attrib,value in div.items():
            if attrib=='type':
                mainDivType = value
                if mainDivOsisID and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}...").format( mainDivOsisID, mainDivType ) )
            elif attrib=="osisID":
                mainDivOsisID = value
                if mainDivType and BibleOrgSysGlobals.verbosityLevel > 2: print( _("Loading {} {}...").format( mainDivOsisID, mainDivType ) )
            elif attrib=='canonical':
                mainDivCanonical = value
            else:
                logging.warning( "93f5 Unprocessed {!r} attribute ({}) in main div element".format( attrib, value ) )
                loadErrors.append( "Unprocessed {!r} attribute ({}) in main div element (93f5)".format( attrib, value ) )
        if not mainDivType or not (mainDivOsisID or mainDivCanonical):
            logging.warning( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
            loadErrors.append( "Incomplete mainDivType {!r} and mainDivOsisID {!r} attributes in main div element".format( mainDivType, mainDivOsisID ) )
        if mainDivType=='book':
            # This is a single book
            if len(mainDivOsisID)>3 and mainDivOsisID[-1] in ('1','2','3',) and mainDivOsisID[-2]=='.': # Fix a bug in the Snowfall USFM to OSIS software
                logging.critical( "Fixing bug in OSIS {!r} book ID".format( mainDivOsisID ) )
                mainDivOsisID = mainDivOsisID[:-2] # Change 1Kgs.1 to 1Kgs
            try:
                BBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromOSIS( mainDivOsisID )
            except KeyError:
                logging.critical( _("{!r} is not a valid OSIS book identifier").format( mainDivOsisID ) )
            if BBB:
                if isinstance( BBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                    if BibleOrgSysGlobals.verbosityLevel > 2: print( "Multiple alternatives for OSIS {!r}: {} (Choosing the first one)".format( mainDivOsisID, BBB ) )
                    BBB = BBB[0]
                if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading {}{}...").format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
                USFMAbbreviation = BibleOrgSysGlobals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                USFMNumber = BibleOrgSysGlobals.BibleBooksCodes.getUSFMNumber( BBB )
                self.thisBook = BibleBook( self, BBB )
                self.thisBook.objectNameString = "OSIS XML Bible Book object"
                self.thisBook.objectTypeString = "OSIS"
                self.haveBook = True
            self.thisBook.addLine( 'id', (USFMAbbreviation if USFMAbbreviation else mainDivOsisID).upper() + " converted to USFM from OSIS by {} V{}".format( ProgName, ProgVersion ) )
            self.thisBook.addLine( 'h', USFMAbbreviation if USFMAbbreviation else mainDivOsisID )
        #elif mainDivType=='bookGroup':
            ## This is all the books lumped in together into one big div
            #if BibleOrgSysGlobals.debugFlag: assert( mainDivCanonical == "true" )
            ## We have to set BBB when we get a chapter reference
            #if BibleOrgSysGlobals.verbosityLevel > 2: print( _("  Loading a book group...") )
            #self.haveBook = False
        else:
            logging.critical( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            loadErrors.append( "What kind of OSIS book div is this? {} {} {}".format( repr(mainDivType), repr(mainDivOsisID), repr(mainDivCanonical) ) )
            if BibleOrgSysGlobals.debugFlag:  halt

        chapterMilestone = verseMilestone = ''
        foundH = False
        for element in div:
########### Title -- could be a book title or (in some OSIS files) a section title (with no way to tell the difference)
#               or even worse still (in the Karen), an alternate chapter number
            if element.tag == OSISXMLBible.OSISNameSpace+'title':
                location = "title of {} div".format( mainDivType )
                validateTitle( element, location, verseMilestone )
########### Div (of the main div) -- most stuff would be expected to be inside a section div inside the book div
            elif element.tag == OSISXMLBible.OSISNameSpace+'div':
                location = "div of {} div".format( mainDivType )
                #if verseMilestone is None: print( location, chapterMilestone ); halt
                BibleOrgSysGlobals.checkXMLNoText( element, location+" at "+verseMilestone, '3f6h', loadErrors )
                BibleOrgSysGlobals.checkXMLNoTail( element, location+" at "+verseMilestone, '0j6h', loadErrors )
                # Process the attributes
                divType = divCanonical = divScope = None
                for attrib,value in element.items():
                    if attrib==OSISXMLBible.XMLNameSpace+"space":
                        divSpace = value
                    elif attrib=='type':
                        divType = value
                        location = value + ' ' + location
                    elif attrib=='canonical':
                        divCanonical = value
                        assert( divCanonical == 'false' )
                    elif attrib=="scope":
                        divScope = value
                    else:
                        logging.warning( "2h56 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (2h56)".format( attrib, value, location, verseMilestone ) )
                # Now process the subelements
                for subelement in element:
###                 ### chapter in div
                    if subelement.tag == OSISXMLBible.OSISNameSpace+"chapter":
                        sublocation = "chapter of " + location
                        chapterMilestone = validateChapterElement( subelement, chapterMilestone, verseMilestone, sublocation )
###                 ### verse in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                        sublocation = "verse of " + location
                        verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
###                 ### title in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'title':  # section heading
                        sublocation = "title of " + location
                        validateTitle( subelement, sublocation, verseMilestone )
                        #if 0:
                            #BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '3d4f', loadErrors )
                            #sectionHeading = subelement.text
                            #titleType = None
                            #for attrib,value in subelement.items():
                                #if attrib=='type':
                                    #titleType = value
                                #else:
                                    #logging.warning( "4h2x Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (4h2x)".format( attrib, value, sublocation, verseMilestone ) )
                            #if chapterMilestone:
                                #bookResults.append( ('title', titleType, sectionHeading,) )
                                #USFMResults.append( ('s', sectionHeading,) )
                            #else: # Must be in the introduction
                                #bookResults.append( ('title', titleType, sectionHeading,) )
                                #USFMResults.append( ('is', sectionHeading,) )
                            #for sub2element in subelement:
                                #if sub2element.tag == OSISXMLBible.OSISNameSpace+'title': # section reference(s)
                                    #sub2location = "title of " + sublocation
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '3d5g', loadErrors )
                                    #sectionReference = sub2element.text
                                    #sectionReferenceType = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='type':
                                            #sectionReferenceType = value
                                        #else:
                                            #logging.warning( "8h4d Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (8h4d)".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                    #if sectionReference:
                                        ##print( divType, self.subDivType, sectionReferenceType ); halt
                                        ##assert( divType=='section' and self.subDivType in ('outline',) and sectionReferenceType=='parallel' )
                                        #if BibleOrgSysGlobals.debugFlag: assert( divType=='section' and sectionReferenceType=='parallel' )
                                        #self.thisBook.addLine( 'sr', clean(sectionReference) )
                                    #for sub3element in sub2element:
                                        #if sub3element.tag == OSISXMLBible.OSISNameSpace+'reference':
                                            #sub3location = "reference of " + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '3d3d', loadErrors )
                                            #referenceText = sub3element.text
                                            #referenceTail = sub3element.tail
                                            #referenceOsisRef = None
                                            #for attrib,value in sub3element.items():
                                                #if attrib=='osisRef':
                                                    #referenceOsisRef = value
                                                #else:
                                                    #logging.warning( "7k43 Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub3element of {} at {} (7k43)".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                            ##print( referenceText, referenceOsisRef, referenceTail )
                                            #bookResults.append( ('reference',referenceText,) )
                                            #USFMResults.append( ('r+',referenceText+referenceTail,) )
                                        #else:
                                            #logging.error( "46g2 Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (46g2)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
###                 ### p in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p': # Most scripture data occurs in here
                        sublocation = "p of " + location
                        verseMilestone = validateParagraph( subelement, sublocation, verseMilestone )
###                 ### list in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'list':
                        sublocation = "list of " + location
                        verseMilestone = validateList( subelement, sublocation, verseMilestone )
###                 ### lg in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'lg':
                        sublocation = "lg of " + location
                        verseMilestone = validateLG( subelement, sublocation, verseMilestone )
###                 ### div in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'div':
                        sublocation = "div of " + location
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2c5bv', loadErrors )
                        subDivType = subDivScope = subDivSpace = canonical = None
                        for attrib,value in subelement.items():
                            if attrib=='type':
                                subDivType = value
                                sublocation = value + ' ' + sublocation
                            elif attrib=="scope":
                                subDivScope = value # Should be an OSIS verse range
                            elif attrib=='canonical':
                                canonical = value
                                assert( canonical in ('true','false',) )
                            elif attrib==self.XMLNameSpace+"space":
                                subDivSpace = value
                                if BibleOrgSysGlobals.debugFlag: assert( subDivSpace == 'preserve' )
                            else:
                                logging.warning( "84kf Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (84kf)".format( attrib, value, sublocation, verseMilestone ) )
                        #print( "self.subDivType", self.subDivType )
                        for sub2element in subelement:
                            if sub2element.tag == OSISXMLBible.OSISNameSpace+'title':
                                sub2location = "title of " + sublocation
                                validateTitle( sub2element, sub2location, verseMilestone )
                                #if 0:
                                    #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '4v5g', loadErrors )
                                    #titleText = clean( sub2element.text, loadErrors, sub2location, verseMilestone )
                                    #titleType = titleSubType = titleCanonicalFlag = None
                                    #for attrib,value in sub2element.items():
                                        #if attrib=='type': titleType = value
                                        #elif attrib=='subType': titleSubType = value
                                        #elif attrib=='canonical': titleCanonicalFlag = value
                                        #else:
                                            #logging.warning( "1d4r Unprocessed {!r} attribute ({}) in {} sub2element of {} at {}".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub2element of {} at {} (1d4r)".format( attrib, value, sub2element.tag, sub2location, verseMilestone ) )
                                    #if titleType: print( "titleType", titleType )
                                    #if BibleOrgSysGlobals.debugFlag:
                                        #if titleType: assert( titleType in ('psalm','parallel','sub',) )
                                        #if titleSubType: assert( titleSubType == 'x-preverse' )
                                    #if titleText:
                                        ##print( divType, subDivType )
                                        #if titleCanonicalFlag=='true' and titleType=='psalm':
                                            #self.thisBook.addLine( 'd', titleText )
                                        #elif divType=='introduction' and subDivType in ('section','outline',):
                                            #self.thisBook.addLine( 'iot' if subDivType == 'outline' else 'is', titleText )
                                        #elif divType=='majorSection' and subDivType=='section':
                                            #self.thisBook.addLine( 'xxxx1' if subDivType == 'outline' else 's1', titleText )
                                        #elif divType=='majorSection' and subDivType=='subSection':
                                            #self.thisBook.addLine( 'xxxx1' if subDivType == 'outline' else 'ms1', titleText )
                                        #elif divType=='section' and subDivType=='subSection':
                                            #self.thisBook.addLine( 'xxxx3' if subDivType == 'outline' else 's', titleText )
                                        #elif divType=='section' and subDivType=='outline':
                                            #self.thisBook.addLine( 'iot', titleText )
                                        #else:
                                            #print( "What title?", divType, subDivType, repr(titleText), titleType, titleSubType, titleCanonicalFlag, verseMilestone )
                                            #if BibleOrgSysGlobals.debugFlag: halt
                                    #for sub3element in sub2element:
                                        #if sub3element.tag == OSISXMLBible.OSISNameSpace+'reference':
                                            #sub3location = "reference of " + sub2location
                                            #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, 'k6l3', loadErrors )
                                            #referenceText = clean( sub3element.text, loadErrors, sub3location, verseMilestone )
                                            #referenceTail = clean( sub3element.tail, loadErrors, sub3location, verseMilestone )
                                            #referenceOsisRef = None
                                            #for attrib,value in sub3element.items():
                                                #if attrib=='osisRef':
                                                    #referenceOsisRef = value
                                                #else:
                                                    #logging.warning( "nm46 Unprocessed {!r} attribute ({}) in {} sub3element of {} at {}".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} sub3element of {} at {} (nm46)".format( attrib, value, sub3element.tag, sub2location, verseMilestone ) )
                                            #logging.error( "Unused {!r} reference field at {}".format( referenceText, sublocation+" at "+verseMilestone ) )
                                            #loadErrors.append( "Unused {!r} reference field at {}".format( referenceText, sublocation+" at "+verseMilestone ) )
                                            #if BibleOrgSysGlobals.debugFlag:
                                                #print( "What's this?", referenceText, referenceOsisRef, referenceTail )
                                                #if debuggingThisModule: halt
                                        #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'note':
                                            #sub3location = "note of " + sub2location
                                            #validateCrossReferenceOrFootnote( sub3element, sub3location, verseMilestone )
                                        #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'hi':
                                            #sub3location = "hi of " + sub2location
                                            #validateHighlight( sub3element, sub3location, verseMilestone ) # Also handles the tail
                                        #else:
                                            #logging.error( "m4g5 Unprocessed {!r} sub3element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                            #loadErrors.append( "Unprocessed {!r} sub3element ({}) in {} at {} (m4g5)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'p':
                                sub2location = "p of " + sublocation
                                verseMilestone = validateParagraph( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'lg':
                                sub2location = "lg of " + sublocation
                                verseMilestone = validateLG( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'list':
                                sub2location = "list of " + sublocation
                                verseMilestone = validateList( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+"chapter":
                                sub2location = "chapter of " + sublocation
                                chapterMilestone = validateChapterElement( sub2element, chapterMilestone, verseMilestone, sub2location )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                sub2location = "verse of " + sublocation
                                verseMilestone = validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'hi':
                                sub2location = "hi of " + sublocation
                                validateHighlight( sub2element, sub2location, verseMilestone )
                            elif sub2element.tag == OSISXMLBible.OSISNameSpace+'lb':
                                sub2location = "lb of " + sublocation
                                validateLB( sub2element, sub2location, verseMilestone )
                            else:
                                logging.error( "14k5 Unprocessed {!r} sub2element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} sub2element ({}) in {} at {} (14k5)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
###                 ### lb in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'lb':
                        sublocation = "lb of " + location
                        validateLB( subelement, sublocation, verseMilestone )
###                 ### closer in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'closer':
                        sublocation = "closer of " + location
                        clsText = clean(subelement.text, loadErrors, sublocation, verseMilestone )
                        clsTail = clean(subelement.tail, loadErrors, sublocation, verseMilestone )
                        BibleOrgSysGlobals.checkXMLNoAttributes( element, location+" at "+verseMilestone, 'js29', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( element, location+" at "+verseMilestone, 'jas7', loadErrors )
                        self.thisBook.appendToLastLine( '\\cls {}\\cls*{}'.format( clsText, clsTail if clsTail else '' ) )
###                 ### table in div
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'table': # not actually written yet! XXXXXXX ...............
                        sublocation = "table of " + location
                        verseMilestone = validateTable( subelement, sublocation, verseMilestone )
                    else:
                        logging.error( "3f67 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (3f67)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        if BibleOrgSysGlobals.debugFlag: halt
########### P
            elif element.tag == OSISXMLBible.OSISNameSpace+'p':
                location = "p of {} div".format( mainDivType )
                verseMilestone = validateParagraph( element, location, verseMilestone )
########### Q
            elif element.tag == OSISXMLBible.OSISNameSpace+"q":
                location = "q of {} div".format( mainDivType )
                qText = element.text
                qTail = element.tail
                # Process the attributes
                sID = eID = level = marker = None
                for attrib,value in element.items():
                    if attrib=="sID": sID = value
                    elif attrib=="eID": eID = value
                    elif attrib=='level': level = value
                    elif attrib=="marker":
                        marker = value
                        if BibleOrgSysGlobals.debugFlag: assert( len(marker) == 1 )
                    else: logging.warning( "6j33 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                # Now process the subelements
                for subelement in element:
                    if subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                        sublocation = "verse of " + location
                        verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+"transChange":
                        sublocation = "transChange of " + location
                        validateTransChange( subelement, sublocation, verseMilestone ) # Also handles the tail
                        #if 0:
                            #text = subelement.text
                            #if BibleOrgSysGlobals.debugFlag: assert( text )
                            #tCTail = subelement.tail
                            ## Process the attributes
                            #transchangeType = None
                            #for attrib,value in subelement.items():
                                #if attrib=='type':
                                    #transchangeType = value
                                #else:
                                    #logging.warning( "821k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                    #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (821k)".format( attrib, value, sublocation, verseMilestone ) )
                            #if BibleOrgSysGlobals.debugFlag: assert( transchangeType in ('added',) )
                            ## Now process the subelements
                            #for sub2element in subelement:
                                #if sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                    #sub2location = "note of " + sublocation
                                    #validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                                    #noteTail = sub2element.tail
                                    #if noteTail: # This is the main text of the verse (follows the inserted note)
                                        #bookResults.append( ('q+', noteTail,) )
                                        #adjNoteTail = noteTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                        #if adjNoteTail: USFMResults.append( ('q+',adjNoteTail,) )
                                #else:
                                    #logging.error( "2j46 Unprocessed {!r} sub2-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    #loadErrors.append( "Unprocessed {!r} sub2-element ({}) in {} at {} (2j46)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                            #if tCTail: # This is the main text of the verse quotation (follows the inserted transChange)
                                #bookResults.append( ('tCq+', tCTail,) )
                                #adjTCTail = tCTail.replace('\n','') # XML line formatting is irrelevant to USFM
                                #if adjTCTail: USFMResults.append( ('tCq+',adjTCTail,) )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                        sublocation = "note of " + location
                        validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                    elif subelement.tag == OSISXMLBible.OSISNameSpace+'p':
                        BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '8h4g', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '2k3m', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoTail( subelement, sublocation+" at "+verseMilestone, '2s7z', loadErrors )
                        p = element.text
                        if p == '¶':
                            bookResults.append( ('paragraph', None,) )
                            bookResults.append( ('p', None,) )
                        else:
                            # print( "p = {!r}".format( element.text ) ); halt
                            bookResults.append( ('paragraph', p,) )
                            bookResults.append( ('p', p,) )
                    else:
                        logging.error( "95k3 Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (95k3)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                        if BibleOrgSysGlobals.debugFlag: halt
########### Chapter
            elif element.tag == OSISXMLBible.OSISNameSpace+"chapter":
                location = "chapter of {} div".format( mainDivType )
                chapterMilestone = validateChapterElement( element, chapterMilestone, verseMilestone, location )
                #print( "BBB is", BBB )
                if chapterMilestone and mainDivType=='bookGroup':
                    #print( "cm", chapterMilestone )
                    OSISBookID = chapterMilestone.split('.')[0]
                    try:
                        newBBB = BibleOrgSysGlobals.BibleBooksCodes.getBBBFromOSIS( OSISBookID )
                    except KeyError:
                        logging.critical( _("{!r} is not a valid OSIS book identifier").format( OSISBookID ) )
                    if newBBB and isinstance( newBBB, list ): # There must be multiple alternatives for BBB from the OSIS one
                        if BibleOrgSysGlobals.verbosityLevel > 2: print( "Multiple alternatives for OSIS {!r}: {} (Choosing the first one)".format( mainDivOsisID, newBBB ) )
                        newBBB = newBBB[0]
                    if newBBB != BBB:
                        BBB = newBBB
                        USFMAbbreviation = BibleOrgSysGlobals.BibleBooksCodes.getUSFMAbbreviation( BBB )
                        USFMNumber = BibleOrgSysGlobals.BibleBooksCodes.getUSFMNumber( BBB )
                        if BibleOrgSysGlobals.verbosityLevel > 1: print( _("  Loading {}{}...").format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
                if chapterMilestone.startswith('chapterContainer.'): # it must have been a container -- process the subelements
                    OSISChapterID = chapterMilestone[17:] # Remove the 'chapterContainer.' prefix
                    chapterBits = OSISChapterID.split( '.' )
                    if BibleOrgSysGlobals.debugFlag: assert( len(chapterBits) == 2 )
                    if BibleOrgSysGlobals.debugFlag: assert( chapterBits[1].isdigit() )
                    self.thisBook.addLine( 'c', chapterBits[1] )

                    def validateMilestone( subelement, location, verseMilestone ):
                        """
                        """
                        sublocation = "milestone of " + location
                        BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'f9s5', loadErrors )
                        BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, 'q9v5', loadErrors )
                        milestoneType = milestoneMarker = milestoneSubtype = milestoneResp = None
                        for attrib,value in subelement.items():
                            if attrib=='type': milestoneType = value
                            elif attrib=="marker": milestoneMarker = value
                            elif attrib=='subType': milestoneSubtype = value
                            elif attrib=="resp": milestoneResp = value
                            else:
                                logging.warning( "8h6k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (8h6k)".format( attrib, value, sublocation, verseMilestone ) )
                        #print( "here bd63", repr(milestoneType) )
                        if BibleOrgSysGlobals.debugFlag:
                            assert( milestoneType in ('x-p','x-extra-p','x-strongsMarkup',) )
                            assert( milestoneMarker in (None,'¶',) ) # What are these?
                            assert( milestoneSubtype in (None,'x-added',) ) # What are these?
                        self.thisBook.addLine( 'p', '' )
                        trailingText = subelement.tail
                        if trailingText and trailingText.strip(): self.thisBook.appendToLastLine( clean(trailingText) )
                        #return subelement.tail if subelement.tail else ''
                    # end of validateMilestone

                    #def handleDivineName( subelement, location, verseMilestone ):
                        #sublocation = "divineName of " + location
                        #BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, '783c', loadErrors )
                        #BibleOrgSysGlobals.checkXMLNoSubelements( subelement, sublocation+" at "+verseMilestone, '7f3c', loadErrors )
                        #if BibleOrgSysGlobals.debugFlag: assert( subelement.text )
                        ##print( "Here hrt5", repr(subelement.text) )
                        #word = "\\nd {}\\nd*".format( subelement.text )
                        #if subelement.tail: word += subelement.tail
                        #return word
                    ## end of handleDivineName

                    #sentence = ""
                    #self.thisBook.addLine( 'v~', '' ) # Start our line
                    for subelement in element:
                        if subelement.tag == OSISXMLBible.OSISNameSpace+'p': # Most scripture data occurs in here
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "p of " + location
                            verseMilestone = validateParagraph( subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'title':  # section heading
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "title of " + location
                            validateTitle( subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'w':
                            validateWord( subelement, location, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+"transChange":
                            validateTransChange( subelement, location, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'divineName':
                            validateDivineName( subelement, location, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+"milestone":
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            validateMilestone( subelement, location, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+"q":
                            sublocation = "q of " + location
                            #words = ""
                            #if subelement.text: words += subelement.text
                            trailingPunctuation = subelement.tail if subelement.tail else ''
                            # Process the attributes
                            qWho = qMarker = None
                            for attrib,value in subelement.items():
                                if attrib=='who': qWho = value
                                elif attrib=="marker": qMarker = value
                                else:
                                    logging.warning( "zq1k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (zq1k)".format( attrib, value, sublocation, verseMilestone ) )
                            #print( 'who', repr(qWho), "marker", repr(qMarker) )
                            for sub2element in subelement:
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                    validateWord( sub2element, sublocation, verseMilestone )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+"transChange":
                                    validateTransChange( sub2element, sublocation, verseMilestone )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'divineName':
                                    validateDivineName( sub2element, sublocation, verseMilestone )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+"milestone":
                                    #sentence += words
                                    #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                                    validateMilestone( sub2element, sublocation, verseMilestone )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'verse':
                                    #sentence += words
                                    #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                                    sub2location = "verse of " + sublocation
                                    verseMilestone = validateVerseElement( sub2element, verseMilestone, chapterMilestone, sub2location )
                                elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                    #sentence += words
                                    #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                                    sub2location = "note of " + sublocation
                                    validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                                else:
                                    logging.error( "d33s Unprocessed {!r} sub-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (d33s)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    if BibleOrgSysGlobals.debugFlag: halt
                            if 0 and qWho=="Jesus": sentence += "\\wj {}\\wj*{}".format( words, trailingPunctuation )
                            else:
                                logging.info( "qWho of {} unused".format( repr(qWho) ) )
                                #sentence += words + trailingPunctuation
                            self.thisBook.addLine( 'q1', '' )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "note of " + location
                            validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+"inscription":
                            #inscription = ""
                            sublocation = "inscription of " + location
                            self.thisBook.appendToLastLine( '\\sc ' )
                            BibleOrgSysGlobals.checkXMLNoText( subelement, sublocation+" at "+verseMilestone, 'r9s5', loadErrors )
                            BibleOrgSysGlobals.checkXMLNoAttributes( subelement, sublocation+" at "+verseMilestone, 'r9v5', loadErrors )
                            for sub2element in subelement:
                                if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                    validateWord( sub2element, sublocation, verseMilestone )
                                else:
                                    logging.error( "4k3s Unprocessed {!r} sub-element ({}) in {} at {}".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (4k3s)".format( sub2element.tag, sub2element.text, sublocation, verseMilestone ) )
                                    if BibleOrgSysGlobals.debugFlag: halt
                            self.thisBook.appendToLastLine( "\\sc*{}".format( clean(subelement.tail) ) )
                            #print( "Here 3c52", repr(sentence) )
                        elif subelement.tag == OSISXMLBible.OSISNameSpace+'verse':
                            #print( "here cx35", repr(sentence) )
                            #if sentence: self.thisBook.appendToLastLine( sentence ); sentence = ""
                            sublocation = "verse of " + location
                            verseMilestone = validateVerseElement( subelement, verseMilestone, chapterMilestone, sublocation )
                            #print( 'vM', verseMilestone ); halt
                            if verseMilestone and verseMilestone.startswith('verseContainer.'): # it must have been a container -- process the subelements
                                #print( "Yikes!" ) # Why??????????????
                                self.thisBook.addLine( 'v', verseMilestone[15:]+' ' ) # Remove the 'verseContainer.' prefix
                                for sub2element in subelement:
                                    if sub2element.tag == OSISXMLBible.OSISNameSpace+'w':
                                        sub2location = "w of " + sublocation
                                        BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '2k3c', loadErrors )
                                        word = sub2element.text
                                        if BibleOrgSysGlobals.debugFlag: assert( word ) # That should be the actual word
                                        # Process the attributes
                                        lemma = morph = None
                                        for attrib,value in sub2element.items():
                                            if attrib=="lemma": lemma = value
                                            elif attrib=="morph": morph = value
                                            else:
                                                logging.warning( "2h54 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub2location, verseMilestone ) )
                                                loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (2h54)".format( attrib, value, sub2location, verseMilestone ) )
                                        # Now process the subelements
                                        segText = segTail = None
                                        for sub3element in sub2element:
                                            if sub3element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                                sub3location = "seg of " + sub2location
                                                BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '43gx', loadErrors )
                                                segText, segTail = sub3element.text, sub3element.tail # XXX unused .............................................
                                                # Process the attributes
                                                for attrib,value in sub3element.items():
                                                    if attrib=='type': segType = value
                                                    else:
                                                        logging.warning( "963k Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub3location, verseMilestone ) )
                                                        loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (963k)".format( attrib, value, sub3location, verseMilestone ) )
                                        self.thisBook.addLine( 'vw', "{} [{}]".format( word,lemma) )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                        sub2location = "seg of " + sublocation
                                        validateSEG( sub2element, sub2location, verseMilestone )
                                        #BibleOrgSysGlobals.checkXMLNoTail( sub2element, sub2location+" at "+verseMilestone, '9s8v', loadErrors )
                                        #BibleOrgSysGlobals.checkXMLNoSubelements( sub2element, sub2location+" at "+verseMilestone, '93dr', loadErrors )
                                        #seg = sub2element.text
                                        #if BibleOrgSysGlobals.debugFlag: assert( seg ) # That should be the actual segment character
                                        ## Process the attributes first
                                        #for attrib,value in sub2element.items():
                                            #if attrib=='type':
                                                #segType = value
                                            #else:
                                                #logging.warning( "5jj2 Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub2location, verseMilestone ) )
                                                #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (5jj2)".format( attrib, value, sub2location, verseMilestone ) )
                                        #self.thisBook.addLine( 'segment', "{} [{}]".format( seg,segType) )
                                    elif sub2element.tag == OSISXMLBible.OSISNameSpace+'note':
                                        sub2location = "note of " + sublocation
                                        validateCrossReferenceOrFootnote( sub2element, sub2location, verseMilestone )
                                        #if 0:
                                            #noteTail = sub2element.tail
                                            #if noteTail: # This is the main text of the verse (follows the inserted note)
                                                #self.thisBook.appendToLastLine( clean(noteTail) )
                                            ## Now process the subelements
                                            #for sub3element in sub2element:
                                                #if sub3element.tag == OSISXMLBible.OSISNameSpace+'catchWord':
                                                    #sub3location = "catchword of " + sub2location
                                                    #BibleOrgSysGlobals.checkXMLNoAttributes( sub3element, sub3location+" at "+verseMilestone, '3d2a', loadErrors )
                                                    #BibleOrgSysGlobals.checkXMLNoSubelements( sub3element, sub3location+" at "+verseMilestone, '0o9i', loadErrors )
                                                    #BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '9k8j', loadErrors )
                                                    #catchWord = sub3element.text
                                                #elif sub3element.tag == OSISXMLBible.OSISNameSpace+'rdg':
                                                    #sub3location = "rdg of " + sub2location
                                                    #validateRDG( sub3element, sub3location, verseMilestone ) # Also handles the tail
                                                    ##if 0:
                                                        ##BibleOrgSysGlobals.checkXMLNoTail( sub3element, sub3location+" at "+verseMilestone, '8h7g', loadErrors )
                                                        ##rdg = sub3element.text
                                                        ### Process the attributes
                                                        ##rdgType = None
                                                        ##for attrib,value in sub3element.items():
                                                            ##if attrib=='type': rdgType = value
                                                            ##else:
                                                                ##logging.warning( "3hgh Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub3location, verseMilestone ) )
                                                                ##loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (3hgh)".format( attrib, value, sub3location, verseMilestone ) )
                                                        ### Now process the subelements
                                                        ##for sub4element in sub3element:
                                                            ##if sub4element.tag == OSISXMLBible.OSISNameSpace+'w':
                                                                ##sub4location = "w of " + sub3location
                                                                ##BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '6g5d', loadErrors )
                                                                ##BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '5r4d', loadErrors )
                                                                ##word = sub4element.text
                                                                ### Process the attributes
                                                                ##lemma = None
                                                                ##for attrib,value in sub4element.items():
                                                                    ##if attrib=="lemma": lemma = value
                                                                    ##else:
                                                                        ##logging.warning( "85kd Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub4location, verseMilestone ) )
                                                                        ##loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (85kd)".format( attrib, value, sub4location, verseMilestone ) )
                                                            ##elif sub4element.tag == OSISXMLBible.OSISNameSpace+'seg':
                                                                ##sub4location = "seg of " + sub3location
                                                                ##BibleOrgSysGlobals.checkXMLNoTail( sub4element, sub4location+" at "+verseMilestone, '5r4q', loadErrors )
                                                                ##BibleOrgSysGlobals.checkXMLNoSubelements( sub4element, sub4location+" at "+verseMilestone, '4s3a', loadErrors )
                                                                ##word = sub4element.text
                                                                ### Process the attributes
                                                                ##segType = None
                                                                ##for attrib,value in sub4element.items():
                                                                    ##if attrib=='type': segType = value
                                                                    ##else:
                                                                        ##logging.warning( "9r5j Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, sub4location, verseMilestone ) )
                                                                        ##loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (9r5j)".format( attrib, value, sub4location, verseMilestone ) )
                                                            ##else:
                                                                ##logging.error( "7k3s Unprocessed {!r} sub-element ({}) in {} at {}".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                                                                ##loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (7k3s)".format( sub4element.tag, sub4element.text, sub3location, verseMilestone ) )
                                                                ##if BibleOrgSysGlobals.debugFlag: halt
                                                #else:
                                                    #logging.error( "9y5g Unprocessed {!r} sub-element ({}) in {} at {}".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                                    #loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (9y5g)".format( sub3element.tag, sub3element.text, sub2location, verseMilestone ) )
                                                    #if BibleOrgSysGlobals.debugFlag: halt
                                    else:
                                        logging.error( "05kq Unprocessed {!r} sub-element {} in {} at {}".format( sub2element.tag, repr(sub2element.text), sublocation, verseMilestone ) )
                                        loadErrors.append( "Unprocessed {!r} sub-element {} in {} at {} (05kq)".format( sub2element.tag, repr(sub2element.text), sublocation, verseMilestone ) )
                                        if BibleOrgSysGlobals.debugFlag: halt
                            elif verseMilestone and verseMilestone.startswith('verseContents#'): # it must have been a container -- process the string
                                print( "verseContents", verseMilestone )
                                bits = verseMilestone.split( '#', 2 )
                                if BibleOrgSysGlobals.debugFlag: assert( len(bits) == 3 )
                                if BibleOrgSysGlobals.debugFlag: assert( bits[0] == 'verseContents' )
                                if BibleOrgSysGlobals.debugFlag: assert( bits[1].isdigit() )
                                if BibleOrgSysGlobals.debugFlag: assert( bits[2] )
                                thisData = bits[1]
                                if bits[2].strip(): thisData += ' ' + bits[2].replace('\n','')
                                #assert( bits[2].strip() )
                                self.thisBook.addLine( 'v', thisData )
                                #print( USFMResults[-4:] )
                                print( self.thisBook._rawLines[-4:] )
                        else:
                            logging.error( "4s9j Unprocessed {!r} sub-element {} in {} at {}".format( subelement.tag, repr(subelement.text), location, verseMilestone ) )
                            loadErrors.append( "Unprocessed {!r} sub-element {} in {} at {} (4s9j)".format( subelement.tag, repr(subelement.text), location, verseMilestone ) )
                            if BibleOrgSysGlobals.debugFlag: halt
########### Verse
            elif element.tag == OSISXMLBible.OSISNameSpace+'verse': # Some OSIS Bibles have verse milestones directly in a bookgroup div
                location = "verse of {} div".format( mainDivType )
                verseMilestone = validateVerseElement( element, verseMilestone, chapterMilestone, location )
########### Lg
            elif element.tag == OSISXMLBible.OSISNameSpace+'lg':
                location = "lg of {} div".format( mainDivType )
                verseMilestone = validateLG( element, location, verseMilestone )
########### TransChange
            elif element.tag == OSISXMLBible.OSISNameSpace+"transChange":
                location = "transChange of {} div".format( mainDivType )
                validateTransChange( element, location, verseMilestone )
                #if 0:
                    #text = element.text
                    #if BibleOrgSysGlobals.debugFlag: assert( text )
                    #tCTail = element.tail
                    ## Process the attributes
                    #transchangeType = None
                    #for attrib,value in element.items():
                        #if attrib=='type':
                            #transchangeType = value
                        #else:
                            #logging.warning( "8k2j Unprocessed {!r} attribute ({}) in {} at {}".format( attrib, value, location, verseMilestone ) )
                            #loadErrors.append( "Unprocessed {!r} attribute ({}) in {} at {} (8k2j)".format( attrib, value, location, verseMilestone ) )
                    #if BibleOrgSysGlobals.debugFlag: assert( transchangeType in ('added',) )
                    ## Now process the subelements
                    #for subelement in element:
                        #if subelement.tag == OSISXMLBible.OSISNameSpace+'note':
                            #sublocation = "note of " + location
                            #validateCrossReferenceOrFootnote( subelement, sublocation, verseMilestone )
                            #noteTail = subelement.tail
                            #if noteTail: # This is the main text of the verse (follows the inserted note)
                                #self.thisBook.appendToLastLine( clean(noteTail) )
                        #else:
                            #logging.error( "2f5z Unprocessed {!r} sub-element ({}) in {} at {}".format( subelement.tag, subelement.text, location, verseMilestone ) )
                            #loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} at {} (2f5z)".format( subelement.tag, subelement.text, location, verseMilestone ) )
                            #if BibleOrgSysGlobals.debugFlag: halt
                    #if tCTail: # This is the main text of the verse (follows the inserted transChange)
                        #bookResults.append( ('tCverse+', tCTail,) )
                        #adjTCTail = tCTail.replace('\n','') # XML line formatting is irrelevant to USFM
                        #if adjTCTail: USFMResults.append( ('tCv~',adjTCTail,) )
########### Note
            elif element.tag == OSISXMLBible.OSISNameSpace+'note':
                location = "note of {} div".format( mainDivType )
                validateCrossReferenceOrFootnote( element, location, verseMilestone )
########### LB
            elif element.tag == OSISXMLBible.OSISNameSpace+'lb':
                location = "lb of {} div".format( mainDivType )
                validateLB( element, location, verseMilestone )
########### List
            elif element.tag == OSISXMLBible.OSISNameSpace+'list':
                location = "list of {} div".format( mainDivType )
                verseMilestone = validateList( element, location, verseMilestone )
########### Table
            elif element.tag == OSISXMLBible.OSISNameSpace+'table':
                location = "table of {} div".format( mainDivType )
                verseMilestone = validateTable( element, location, verseMilestone )
########### Left-overs!
            else:
                logging.error( "5ks1 Unprocessed {!r} sub-element ({}) in {} div at {}".format( element.tag, element.text, mainDivType, verseMilestone ) )
                loadErrors.append( "Unprocessed {!r} sub-element ({}) in {} div at {} (5ks1)".format( element.tag, element.text, mainDivType, verseMilestone ) )
                if BibleOrgSysGlobals.debugFlag: halt
            #if element.tail is not None and element.tail.strip(): logging.error( "Unexpected left-over {!r} tail data after {} element in {} div at {}".format( element.tail, element.tag, mainDivType, verseMilestone ) )

        #print( "Done Validating", BBB, mainDivOsisID, mainDivType )
        #print( "bookResults", bookResults )
        if BBB:
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  Saving {}{} book into results...".format( self.abbreviation+' ' if self.abbreviation else '', BBB ) )
            #print( mainDivOsisID, "results", BBB, bookResults[:10], "..." )
            #if bookResults: self.bkData[BBB] = bookResults
            #if USFMResults: self.USFMBooks[BBB] = USFMResults
            self.saveBook( self.thisBook )
    # end of OSISXMLBible.validateAndExtractBookDiv


    #def getVerseDataList( self, reference ):
        #"""Returns a list of 2-tuples containing (word, lemma)."""
        #assert( len(reference) == 3 ) # BBB,C,V
        #BBB, chapterString, verseString = reference
        #assert( isinstance(BBB,str) and len(BBB)==3 )
        #assert( BBB in BibleOrgSysGlobals.BibleBooksCodes )
        #assert( isinstance( chapterString, str ) )
        #assert( isinstance( verseString, str ) )
        #if BBB in self.books:
            #foundChapter, foundVerse, result = False, False, []
            #for info in self.books[BBB]:
                #if len(info)==2:
                    #name, value = info
                    #if name == 'chapter':
                        #foundChapter = value == chapterString
                        #foundVerse = False
                    #if foundChapter and name=='verse': foundVerse = value == verseString
                    #if foundVerse:
                        #if name=='word': result.append( value )
                        #elif name=='segment': result.append( value )
                        #elif name!='chapter' and name!='verse': print( "OSISXMLBible got", name, value )
            #return result
    ## end of getVerseData

    #def getVerseText( self, reference ):
        #"""Returns the text for the verse."""
        #assert( len(reference) == 3 ) # BBB,C,V
        #result = ''
        #data = self.getVerseDataList( reference )
        #if data:
            #for word, lemma in data: # throw away the lemma data and segment types
                #if result: result += ' '
                #result += word
            #return result
# end of OSISXMLBible class


def demo():
    """
    Main program to handle command line parameters and then run what they want.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )


    if 1: # Test OSISXMLBible object
        testFilepaths = (
            "Tests/DataFilesForTests/OSISTest1/", # Matigsalug test sample
            "Tests/DataFilesForTests/OSISTest2/", # Full KJV from Crosswire
            #"../morphhb/wlc/Ruth.xml", "../morphhb/wlc/Dan.xml", "../morphhb/wlc/", # Hebrew Ruth, Daniel, Bible
            #"../../../../../Data/Work/Bibles/Formats/OSIS/Crosswire USFM-to-OSIS (Perl)/Matigsalug.osis.xml", # Entire Bible in one file 4.4MB
            #"../../MatigsalugOSIS/OSIS-Output/MBTGEN.xml",
            #"../../MatigsalugOSIS/OSIS-Output/MBTRUT.xml", # Single books
            #"../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml", # Single books
            #    "../../MatigsalugOSIS/OSIS-Output/MBTMRK.xml", "../../MatigsalugOSIS/OSIS-Output/MBTJAS.xml", # Single books
            #    "../../MatigsalugOSIS/OSIS-Output/MBT2PE.xml", # Single book
            #"../../MatigsalugOSIS/OSIS-Output", # Entire folder of single books
            )
        justOne = ( testFilepaths[0], )

        # Demonstrate the OSIS Bible class
        #for j, testFilepath in enumerate( justOne ): # Choose testFilepaths or justOne
        for j, testFilepath in enumerate( testFilepaths ): # Choose testFilepaths or justOne
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "\nOSIS {}/ Demonstrating the OSIS Bible class...".format( j+1 ) )
            if BibleOrgSysGlobals.verbosityLevel > 0: print( "  Test filepath is {!r}".format( testFilepath ) )
            oB = OSISXMLBible( testFilepath ) # Load and process the XML
            oB.load()
            if BibleOrgSysGlobals.verbosityLevel > 0: print( oB ) # Just print a summary

            if 1: # Test verse lookup
                import VerseReferences
                for referenceTuple in ( ('OT','GEN','1','1'), ('OT','GEN','1','3'),
                                    ('OT','RUT','1','1'), ('OT','RUT','3','3'),
                                    ('OT','PSA','3','0'), ('OT','PSA','3','1'),
                                    ('OT','DAN','1','21'),
                                    ('NT','MAT','3','5'), ('NT','JAM','1','6'),
                                    ('NT','JDE','1','4'), ('NT','REV','22','21'),
                                    ('DC','BAR','1','1'), ('DC','MA1','1','1'), ('DC','MA2','1','1',), ):
                    (t, b, c, v) = referenceTuple
                    if t=='OT' and len(oB)==27: continue # Don't bother with OT references if it's only a NT
                    if t=='NT' and len(oB)==39: continue # Don't bother with NT references if it's only a OT
                    if t=='DC' and len(oB)<=66: continue # Don't bother with DC references if it's too small
                    try:
                        svk = VerseReferences.SimpleVerseKey( b, c, v )
                        #print( svk, oB.getVerseDataList( svk ) )
                        print( "OSISXMLBible.demo:", svk, oB.getVerseText( svk ) )
                    except KeyError:
                        print( "OSISXMLBible.demo: {} {}:{} can't be found!".format( b, c, v ) )

            if BibleOrgSysGlobals.strictCheckingFlag or BibleOrgSysGlobals.debugFlag:
                oB.check()
            if BibleOrgSysGlobals.commandLineOptions.export:
                #oB.toODF(); halt
                oB.doAllExports( wantPhotoBible=False, wantODFs=False, wantPDFs=False )
# end of demo

if __name__ == '__main__':
    # Configure basic set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser, exportAvailable=True )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of OSISXMLBible.py