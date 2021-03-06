#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# InternalBible.py
#
# Module handling the USFM markers for Bible books
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
Module for defining and manipulating Bibles in our internal USFM-based 'lines' format.

The calling class needs to call this base class __init__ routine and also set:
    self.objectTypeString (e.g., "USFM" or "USX")
    self.objectNameString (with a description of the type of Bible object, e.g., "USFM Bible object")

It also needs to provide a "load" routine that sets any of the relevant fields:
    self.sourceFolder, self.sourceFilename, self.sourceFilepath, self.fileExtension
    self.name, self.givenName, self.shortName, self.abbreviation
    self.status, self.revision, self.version

If you have access to any metadata, that goes in
    self.ssfFilepath, self.ssfDict, self.settingsDict

and then fills
    self.books by calling saveBook() which updates:
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict
"""

from gettext import gettext as _

LastModifiedDate = '2015-04-30' # by RJH
ShortProgName = "InternalBible"
ProgName = "Internal Bible handler"
ProgVersion = '0.62'
ProgNameVersion = '{} v{}'.format( ShortProgName, ProgVersion )
ProgNameVersionDate = '{} {} {}'.format( ProgNameVersion, _("last modified"), LastModifiedDate )

debuggingThisModule = False


import os, logging
from collections import OrderedDict

import BibleOrgSysGlobals
from InternalBibleInternals import InternalBibleEntryList
from InternalBibleBook import BCV_VERSION


OT39BookList = ( 'GEN', 'EXO', 'LEV', 'NUM', 'DEU', 'JOS', 'JDG', 'RUT', 'SA1', 'SA2', 'KI1', 'KI2', 'CH1', 'CH2', \
        'EZR', 'NEH', 'EST', 'JOB', 'PSA', 'PRO', 'ECC', 'SNG', 'ISA', 'JER', 'LAM', 'EZE', 'DAN', \
        'HOS', 'JOL', 'AMO', 'OBA', 'JNA', 'MIC', 'NAH', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL' )
assert( len(OT39BookList) == 39 )
NT27BookList = ( 'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', 'CO1', 'CO2', 'GAL', 'EPH', 'PHP', 'COL', \
        'TH1', 'TH2', 'TI1', 'TI2', 'TIT', 'PHM', 'HEB', 'JAM', 'PE1', 'PE2', 'JN1', 'JN2', 'JN3', 'JDE', 'REV' )
assert( len(NT27BookList) == 27 )


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



class InternalBible:
    """
    Class to define and manipulate InternalBibles.

    The BibleWriter class is based on this class.

    This class contains no load function -- that is expected to be supplied by the superclass.
    """
    def __init__( self ):
        """
        Create the object.
        """
        # Set up empty variables for the object
        #       some of which will be filled in later depending on what is known from the Bible type
        self.name = self.givenName = self.shortName = self.abbreviation = None
        self.sourceFolder = self.sourceFilename = self.sourceFilepath = self.fileExtension = None
        self.status = self.revision = self.version = None

        # Set up empty containers for the object
        self.books = OrderedDict()
        self.ssfFilepath, self.ssfDict, self.settingsDict = '', {}, {}
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict, self.bookAbbrevDict = {}, {}, {}, {} # Used to store book name and abbreviations (pointing to the BBB codes)
        self.reverseDict, self.guesses = {}, '' # A program history
        self.loadedAllBooks, self.triedLoadingBook = False, {}
        self.divisions = OrderedDict()
        self.errorDictionary = OrderedDict()
        self.errorDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary
    # end of InternalBible.__init_


    def __str__( self ):
        """
        This method returns the string representation of a Bible.

        @return: the name of a Bible object formatted as a string
        @rtype: string
        """
        result = self.objectNameString
        indent = 2
        if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: result += ' v' + ProgVersion
        if self.name: result += ('\n' if result else '') + ' '*indent + _("Name: {}").format( self.name )
        if self.abbreviation: result += ('\n' if result else '') + ' '*indent + _("Abbreviation: {}").format( self.abbreviation )
        if self.sourceFolder: result += ('\n' if result else '') + ' '*indent + _("Source folder: {}").format( self.sourceFolder )
        elif self.sourceFilepath: result += ('\n' if result else '') + ' '*indent + _("Source: {}").format( self.sourceFilepath )
        if BibleOrgSysGlobals.verbosityLevel > 1:
            for fieldName in ( 'Title', 'Version', 'Revision',  ):
                if fieldName in self.settingsDict:
                    result += ('\n' if result else '') + ' '*indent + _("{}: {!r}").format( fieldName, self.settingsDict[fieldName] )
        if BibleOrgSysGlobals.verbosityLevel > 2:
            for fieldName in ( 'Status', 'Font', 'Copyright', ):
                if fieldName in self.settingsDict:
                    result += ('\n' if result else '') + ' '*indent + _("{}: {!r}").format( fieldName, self.settingsDict[fieldName] )
        #if self.revision: result += ('\n' if result else '') + ' '*indent + _("Revision: {}").format( self.revision )
        #if self.version: result += ('\n' if result else '') + ' '*indent + _("Version: {}").format( self.version )
        result += ('\n' if result else '') + ' '*indent + _("Number of{} books: {}{}") \
                                        .format( '' if self.loadedAllBooks else ' loaded', len(self.books), ' {}'.format( self.getBookList() ) if 0<len(self.books)<5 else '' )
        return result
    # end of InternalBible.__str__


    def __len__( self ):
        """
        This method returns the number of loaded books in the Bible.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( t("__len__ result is unreliable because all books not loaded!") )
        return len( self.books )
    # end of InternalBible.__len__


    def __contains__( self, BBB ):
        """
        This method checks whether the Bible (as loaded so far) contains the BBB book.

        Returns True or False.
        """
        if BibleOrgSysGlobals.debugFlag: assert( isinstance(BBB,str) and len(BBB)==3 )
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and not self.loadedAllBooks:
            logging.critical( t("__contains__ result is unreliable because all books not loaded!") )
        return BBB in self.books
    # end of InternalBible.__contains__


    def __getitem__( self, keyIndex ):
        """
        Given an index integer, return the book object (or raise an IndexError)

        This function also accepts a BBB so you can use it to get a book from the Bible by BBB.
        """
        #print( t("__getitem__( {} )").format( keyIndex ) )
        #print( list(self.books.items()) )
        if isinstance( keyIndex, int ):
            return list(self.books.items())[keyIndex][1] # element 0 is BBB, element 1 is the book object
        if isinstance( keyIndex, str ) and len(keyIndex)==3: # assume it's a BBB
            return self.books[keyIndex]
    # end of InternalBible.__getitem__


    def __iter__( self ):
        """
        Yields the next book object.

        NOTE: Most other functions return the BBB -- this returns the actual book object!
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( t("__iter__ result is unreliable because all books not loaded!") )
        for BBB in self.books:
            yield self.books[BBB]
    # end of InternalBible.__iter__


    def containsAnyOT39Books( self ):
        """
        Returns True if any of the 39 common OT books are present.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( t("containsAnyOT39Books result is unreliable because all books not loaded!") )
        for BBB in OT39BookList:
            if BBB in self: return True
        return False
    #end of InternalBible.containsAnyOT39Books


    def containsAnyNT27Books( self ):
        """
        Returns True if any of the 27 common NT books are present.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( t("containsAnyNT27Books result is unreliable because all books not loaded!") )
        for BBB in NT27BookList:
            if BBB in self: return True
        return False
    #end of InternalBible.containsAnyNT27Books


    def __getNames( self ):
        """
        Try to improve our names.

        This method should be called once all books are loaded.
        May be called again if external metadata is also loaded.
        """
        #print( "InternalBible.__getNames()" )
        if not self.abbreviation and 'WorkAbbreviation' in self.settingsDict: self.abbreviation = self.settingsDict['WorkAbbreviation']
        if not self.name and 'FullName' in self.ssfDict: self.name = self.ssfDict['FullName']
        if not self.shortName and 'Name' in self.ssfDict: self.shortName = self.ssfDict['Name']
        self.projectName = self.name if self.name else "Unknown"

        if self.settingsDict: # we have metadata loaded
            for BBB in self.books:
                for fieldName in self.settingsDict:
                    if fieldName.startswith( BBB ):
                        self.books[BBB].getAssumedBookNames() # don't need the returned result
                        break
    # end of InternalBible.__getNames


    def loadBookIfNecessary( self, BBB ):
        """
        """
        if BBB not in self.books and BBB not in self.triedLoadingBook:
            try: self.loadBook( BBB ) # Some types of Bibles have this function (so an entire Bible doesn't have to be loaded at startup)
            except AttributeError: logging.info( "No function to load individual Bible book: {}".format( BBB ) ) # Ignore errors
            except FileNotFoundError: logging.info( "Unable to find and load individual Bible book: {}".format( BBB ) ) # Ignore errors
            self.triedLoadingBook[BBB] = True
    # end of InternalBible.loadBookIfNecessary


    def reloadBook( self, BBB ):
        """
        Tries to load or reload a book.
        """
        if BibleOrgSysGlobals.debugFlag: print( t("reloadBook( {} )...").format( BBB ) )
        #if BBB not in self.books and BBB not in self.triedLoadingBook:
        try: self.loadBook( BBB ) # Some types of Bibles have this function (so an entire Bible doesn't have to be loaded at startup)
        except AttributeError: logging.info( "No function to load individual Bible book: {}".format( BBB ) ) # Ignore errors
        except FileNotFoundError: logging.info( "Unable to find and load individual Bible book: {}".format( BBB ) ) # Ignore errors
        self.triedLoadingBook[BBB] = True
        #try: del self.discoveryResults # These are now out-of-date
        #except KeyError:
            #if BibleOrgSysGlobals.debugFlag: print( t("reloadBook has no discoveryResults to delete") )
        if 'discoveryResults' in dir(self): # need to update them
            # Need to double-check that this doesn't cause any double-ups .....................XXXXXXXXXXXXXXXXXXXXXX
            self.books[BBB]._discover( self.discoveryResults )
            self._aggregateDiscoveryResults()
    # end of InternalBible.loadBookIfNecessary


    def doPostLoadProcessing( self ):
        """
        This method should be called once all books are loaded to do critical book-keeping.

        Doesn't do a "discover" yet, coz this is quite time-consuming.
        """
        self.loadedAllBooks = True

        # Try to improve our names (may also be called from loadMetadataFile)
        self.__getNames()

        # Discover what we've got loaded so we don't have to worry about doing it later
        #self.discover()
    # end of InternalBible.doPostLoadProcessing


    def xxxunloadBooks( self ):
        """
        Called to unload books, usually coz one or more of them has been edited.
        """
        if BibleOrgSysGlobals.debugFlag: print( t("unloadBooks()...") )
        self.books = OrderedDict()
        self.BBBToNameDict, self.bookNameDict, self.combinedBookNameDict, self.bookAbbrevDict = {}, {}, {}, {} # Used to store book name and abbreviations (pointing to the BBB codes)
        self.reverseDict, self.guesses = {}, '' # A program history
        self.loadedAllBooks, self.triedLoadingBook = False, {}
        self.divisions = OrderedDict()
        self.errorDictionary = OrderedDict()
        self.errorDictionary['Priority Errors'] = [] # Put this one first in the ordered dictionary

        try: del self.discoveryResults # These are now irrelevant
        except KeyError:
            if BibleOrgSysGlobals.debugFlag: print( t("unloadBooks has no discoveryResults to delete") )
    # end of InternalBible.unloadBooks


    def loadMetadataFile( self, mdFilepath ):
        """
        Load the fields from the given metadata text file into self.settingsDict.
        """
        def saveMD( fieldName, contents ):
            """
            Save an entry in the settings dictionary
                but check for duplicates first.
            """
            if fieldName in self.settingsDict: # We have a duplicate
                logging.warning("About to replace {}={} from metadata file".format( repr(fieldName), repr(self.settingsDict[fieldName]) ) )
            else: # Also check for "duplicates" with a different case
                ucFieldName = fieldName.upper()
                for key in self.settingsDict:
                    ucKey = key.upper()
                    if ucKey == ucFieldName:
                        logging.warning("About to add {} from metadata file even though already have {}".format( repr(fieldName), repr(key) ) )
                        break
            self.settingsDict[fieldName] = BibleOrgSysGlobals.makeSafeString( contents )
        # end of loadMetadataFile.saveMD

        # main code for loadMetadataFile()
        logging.info( "Loading supplied project metadata..." )
        if BibleOrgSysGlobals.verbosityLevel > 1: print( "Loading supplied project metadata..." )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "Old metadata settings", len(self.settingsDict), self.settingsDict )
        lineCount, continuedFlag = 0, False
        with open( mdFilepath, 'rt' ) as mdFile:
            for line in mdFile:
                while line and line[-1] in '\n\r': line=line[:-1] # Remove trailing newline characters (Linux or Windows)
                #print( "MD line: {!r}".format( line ) )
                if not line: continue # Just discard additional blank lines
                lineCount += 1
                if line[0] == '#': continue # Just discard comment lines
                if not continuedFlag:
                    if '=' not in line:
                        logging.warning( t("loadMetadataFile: Missing equals sign from metadata line (ignored): {}").format( repr(line) ) )
                    else: # Seems like a field=something type line
                        bits = line.split( '=', 1 )
                        assert( len(bits) == 2 )
                        fieldName = bits[0]
                        fieldContents = bits[1]
                        if fieldContents.endswith( '\\' ):
                            continuedFlag = True
                            fieldContents = fieldContents[:-1] # Remove the continuation character
                        else:
                            if not fieldContents:
                                logging.warning( "Metadata line has a blank entry for {}".format( repr(fieldName) ) )
                            saveMD( fieldName, fieldContents )
                else: # continuedFlag
                    if line.endswith( '\\' ): line = line[:-1] # Remove the continuation character
                    else: continuedFlag = False
                    fieldContents += line
                    if not continuedFlag:
                        logging.warning( t("loadMetadataFile: Metadata lines result in a blank entry for {}").format( repr(fieldName) ) )
                        saveMD( fieldName, fieldContents )
            if BibleOrgSysGlobals.verbosityLevel > 1: print( "  {} non-blank lines read from uploaded metadata file".format( lineCount ) )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "New metadata settings", len(self.settingsDict), self.settingsDict )

        # Try to improve our names (also called earlier from doPostLoadProcessing)
        self.__getNames()
    # end of InternalBible.loadMetadataFile


    def getBookList( self ):
        """
        Returns a list of loaded book codes.
        """
        if BibleOrgSysGlobals.debugFlag and not self.loadedAllBooks:
            logging.critical( t("getBookList result is unreliable because all books not loaded!") )
        return [BBB for BBB in self.books]


    def pickle( self, filename=None, folder=None ):
        """
        Writes the object to a .pickle file that can be easily loaded into a Python3 program.
            If folder is None (or missing), defaults to the default cache folder specified in BibleOrgSysGlobals.
            Created the folder(s) if necessary.
        """
        #print( "pickle( *, {}, {} )".format( repr(filename), repr(folder ) ) )
        #print( repr(self.objectNameString), repr(self.objectTypeString) )
        #print( (self.abbreviation), repr(self.name) )
        if filename is None:
            filename = self.abbreviation if self.abbreviation else self.name
        if BibleOrgSysGlobals.debugFlag: assert( filename )
        filename = BibleOrgSysGlobals.makeSafeFilename( filename ) + '.pickle'
        if BibleOrgSysGlobals.verbosityLevel > 2:
            print( t("pickle: Saving {} to {}...") \
                .format( self.objectNameString, filename if folder is None else os.path.join( folder, filename ) ) )
        BibleOrgSysGlobals.pickleObject( self, filename, folder )
    # end of InternalBible.pickle


    def getAssumedBookName( self, BBB ):
        """Gets the book name for the given book reference code."""
        if BibleOrgSysGlobals.debugFlag: assert( BBB in BibleOrgSysGlobals.BibleBooksCodes)
        #if BBB in self.BBBToNameDict: return self.BBBToNameDict[BBB] # What was this ???
        try: return self.books[BBB].assumedBookName
        except (KeyError, AttributeError): return None
    # end of InternalBible.getAssumedBookName


    def getLongTOCName( self, BBB ):
        """Gets the long table of contents book name for the given book reference code."""
        if BibleOrgSysGlobals.debugFlag: assert( BBB in BibleOrgSysGlobals.BibleBooksCodes)
        try: return self.books[BBB].longTOCName
        except (KeyError, AttributeError): return None
    # end of InternalBible.getLongTOCName


    def getShortTOCName( self, BBB ):
        """Gets the short table of contents book name for the given book reference code."""
        if BibleOrgSysGlobals.debugFlag: assert( BBB in BibleOrgSysGlobals.BibleBooksCodes)
        try: return self.books[BBB].shortTOCName
        except (KeyError, AttributeError): return None
    # end of InternalBible.getShortTOCName


    def getBooknameAbbreviation( self, BBB ):
        """Gets the book abbreviation for the given book reference code."""
        if BibleOrgSysGlobals.debugFlag: assert( BBB in BibleOrgSysGlobals.BibleBooksCodes)
        try: return self.books[BBB].booknameAbbreviation
        except (KeyError, AttributeError): return None
    # end of InternalBible.getBooknameAbbreviation


    def saveBook( self, bookData ):
        """
        Save the Bible book into our object
            and uupdate our indexes.
        """
        #print( "saveBook( {} )".format( bookData ) )
        BBB = bookData.BBB
        if BBB in self.books: # already
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel > 2:
                print( t("saveBook: Already have"), self.getBookList() )
            logging.critical( t("saveBook: overwriting already existing {} book!").format( BBB ) )
        self.books[BBB] = bookData
        # Make up our book name dictionaries while we're at it
        assumedBookNames = bookData.getAssumedBookNames()
        for assumedBookName in assumedBookNames:
            self.BBBToNameDict[BBB] = assumedBookName
            assumedBookNameLower = assumedBookName.lower()
            self.bookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
            self.combinedBookNameDict[assumedBookNameLower] = BBB # Store the deduced book name (just lower case)
            if ' ' in assumedBookNameLower: self.combinedBookNameDict[assumedBookNameLower.replace(' ','')] = BBB # Store the deduced book name (lower case without spaces)
    # end of InternalBible.saveBook


    def guessXRefBBB( self, referenceString ):
        """
        Attempt to return a book reference code given a book reference code (e.g., 'PRO'),
                a book name (e.g., Proverbs) or abbreviation (e.g., Prv).
            Uses self.combinedBookNameDict and makes and uses self.bookAbbrevDict.
            Return None if unsuccessful."""
        if BibleOrgSysGlobals.debugFlag: assert( referenceString and isinstance( referenceString, str ) )
        result = BibleOrgSysGlobals.BibleBooksCodes.getBBB( referenceString )
        if result is not None: return result # It's already a valid BBB

        adjRefString = referenceString.lower()
        if adjRefString in self.combinedBookNameDict:
            BBB = self.combinedBookNameDict[adjRefString]
            #assert( BBB not in self.reverseDict )
            self.reverseDict[BBB] = referenceString
            return BBB # Found a whole name match
        if adjRefString in self.bookAbbrevDict:
            BBB = self.bookAbbrevDict[adjRefString]
            #print( referenceString, adjRefString, BBB, self.reverseDict )
            #assert( BBB not in self.reverseDict )
            self.reverseDict[BBB] = referenceString
            return BBB # Found a whole abbreviation match

        # Do a program check
        for BBB in self.reverseDict: assert( self.reverseDict[BBB] != referenceString )

        # See if a book name starts with this string
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  getXRefBBB using startswith1..." )
        count = 0
        for bookName in self.bookNameDict:
            if bookName.startswith( adjRefString ):
                BBB = self.bookNameDict[bookName]
                count += 1
        if count == 1: # Found exactly one
            self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
            self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith1)".format( referenceString, BBB )
            self.reverseDict[BBB] = referenceString
            return BBB
        elif count == 2: # Found exactly two but one of them might have a different abbreviation that we already know
            secondCount = 0
            for bookName in self.bookNameDict: # Gotta go through them all again now :(
                if bookName.startswith( adjRefString ):
                    BBBx = self.bookNameDict[bookName]
                    if BBBx not in self.reverseDict: BBB = BBBx; secondCount += 1
            if secondCount == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith1SECOND)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
            print( t("  guessXRefBBB has multiple startswith matches for {!r} in {}").format( adjRefString, self.combinedBookNameDict ) )
        if count == 0:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  getXRefBBB using startswith2..." )
            for bookName in self.combinedBookNameDict:
                if bookName.startswith( adjRefString ):
                    BBB = self.combinedBookNameDict[bookName]
                    count += 1
            if count == 1: # Found exactly one now
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith2)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
        elif count == 2: # Found exactly two but one of them might have a different abbreviation that we already know
            secondCount = 0
            for bookName in self.bookNameDict: # Gotta go through them all again now :(
                if bookName.startswith( adjRefString ):
                    BBBx = self.bookNameDict[bookName]
                    if BBBx not in self.reverseDict: BBB = BBBx; secondCount += 1
            if secondCount == 1: # Found exactly one now
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (startswith2SECOND)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB

        # See if a book name contains a word that starts with this string
        if count == 0:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( "  getXRefBBB using word startswith..." )
            for bookName in self.bookNameDict:
                if ' ' in bookName:
                    for bit in bookName.split():
                        if bit.startswith( adjRefString ):
                            BBB = self.bookNameDict[bookName]
                            count += 1
            if count == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (word startswith)".format( referenceString, BBB )
                self.reverseDict[BBB] = referenceString
                return BBB
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
                print( t("  guessXRefBBB has multiple startswith matches for {!r} in {}").format( adjRefString, self.bookNameDict ) )

        # See if a book name starts with the same letter plus contains the letters in this string (slow)
        if count == 0:
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("  guessXRefBBB using first plus other characters...") )
            for bookName in self.bookNameDict:
                if not bookName: print( self.bookNameDict ); halt # temp...
                #print( "aRS={!r}, bN={!r}".format( adjRefString, bookName ) )
                if adjRefString[0] != bookName[0]: continue # The first letters don't match
                found = True
                for char in adjRefString[1:]:
                    if char not in bookName[1:]: # We could also check that they're in the correct order........................might give less ambiguities???
                        found = False
                        break
                if not found: continue
                #print( "  getXRefBBB: p...", bookName )
                BBB = self.bookNameDict[bookName]
                count += 1
            if count == 1: # Found exactly one
                self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (firstletter+)".format( referenceString, BBB )
                return BBB
            if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
                print( t("  guessXRefBBB has first and other character multiple matches for {!r} in {}").format( adjRefString, self.bookNameDict ) )

        if 0: # Too error prone!!!
            # See if a book name contains the letters in this string (slow)
            if count == 0:
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print ("  getXRefBBB using characters..." )
                for bookName in self.bookNameDict:
                    found = True
                    for char in adjRefString:
                        if char not in bookName: # We could also check that they're in the correct order........................might give less ambiguities???
                            found = False
                            break
                    if not found: continue
                    #print( "  getXRefBBB: q...", bookName )
                    BBB = self.bookNameDict[bookName]
                    count += 1
                if count == 1: # Found exactly one
                    self.bookAbbrevDict[adjRefString] = BBB # Save to make it faster next time
                    self.guesses += ('\n' if self.guesses else '') + "Guessed {!r} to be {} (letters)".format( referenceString, BBB )
                    return BBB
                if BibleOrgSysGlobals.debugFlag and debuggingThisModule and count > 1:
                    print( t("  guessXRefBBB has character multiple matches for {!r} in {}").format( adjRefString, self.bookNameDict ) )

        if BibleOrgSysGlobals.debugFlag and debuggingThisModule or BibleOrgSysGlobals.verbosityLevel>2:
            print( t("  guessXRefBBB failed for {!r} with {} and {}").format( referenceString, self.bookNameDict, self.bookAbbrevDict ) )
        string = "Couldn't guess {!r}".format( referenceString[:5] )
        if string not in self.guesses: self.guesses += ('\n' if self.guesses else '') + string
    # end of InternalBible.guessXRefBBB


    def getVersification( self ):
        """
        Get the versification of the Bible into four ordered dictionaries with the referenceAbbreviation as key.
            Entries in both are lists of tuples, being (c, v).
            The first list contains an entry for each chapter in the book showing the number of verses.
            The second list contains an entry for each missing verse in the book (not including verses that are missing at the END of a chapter).
            The third list contains an entry for combined verses in the book.
            The fourth list contains an entry for reordered verses in the book.
        """
        if BibleOrgSysGlobals.debugFlag: assert( self.books )
        totalVersification, totalOmittedVerses, totalCombinedVerses, totalReorderedVerses = OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict()
        for BBB in self.books.keys():
            versification, omittedVerses, combinedVerses, reorderedVerses = self.books[BBB].getVersification()
            totalVersification[BBB] = versification
            if omittedVerses: totalOmittedVerses[BBB] = omittedVerses # Only add an entry if there are some
            if combinedVerses: totalCombinedVerses[BBB] = combinedVerses
            if reorderedVerses: totalReorderedVerses[BBB] = reorderedVerses
        return totalVersification, totalOmittedVerses, totalCombinedVerses, totalReorderedVerses
    # end of InternalBible.getVersification


    def getAddedUnits( self ):
        """
        Get the added units in the Bible text, such as section headings, paragraph breaks, and section references.
        """
        if BibleOrgSysGlobals.debugFlag: assert( self.books )
        haveParagraphs = haveQParagraphs = haveSectionHeadings = haveSectionReferences = haveWordsOfJesus = False
        AllParagraphs, AllQParagraphs, AllSectionHeadings, AllSectionReferences, AllWordsOfJesus = OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict(), OrderedDict()
        for BBB in self.books:
            paragraphReferences, qReferences, sectionHeadings, sectionReferences, wordsOfJesus = self.books[BBB].getAddedUnits()
            if paragraphReferences: haveParagraphs = True
            AllParagraphs[BBB] = paragraphReferences # Add an entry for each given book, even if the entry is blank
            if qReferences: haveQParagraphs = True
            AllQParagraphs[BBB] = qReferences
            if sectionHeadings: haveSectionHeadings = True
            AllSectionHeadings[BBB] = sectionHeadings
            if sectionReferences: haveSectionReferences = True
            AllSectionReferences[BBB] = sectionReferences
            if wordsOfJesus: haveWordsOfJesus = True
            AllWordsOfJesus[BBB] = wordsOfJesus
        # If a version lacks a feature completely, return None (rather than an empty dictionary)
        return AllParagraphs if haveParagraphs else None, AllQParagraphs if haveQParagraphs else None, AllSectionHeadings if haveSectionHeadings else None, AllSectionReferences if haveSectionReferences else None, AllWordsOfJesus if haveWordsOfJesus else None
    # end of InternalBible.getAddedUnits


    def discover( self ):
        """
        Runs a series of checks and count on each book of the Bible
            in order to try to determine what are the normal standards.
        """
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "InternalBible:discover()" )
        if BibleOrgSysGlobals.debugFlag and 'discoveryResults' in dir(self):
            logging.warning( t("discover: We had done this already!") ) # We've already called this once
            halt

        self.discoveryResults = OrderedDict()

        # Get our recommendations for added units -- only load this once per Bible
        #import pickle
        #folder = os.path.join( os.path.dirname(__file__), "DataFiles/", "ScrapedFiles/" ) # Relative to module, not cwd
        #filepath = os.path.join( folder, "AddedUnitData.pickle" )
        #if BibleOrgSysGlobals.verbosityLevel > 3: print( t("Importing from {}...").format( filepath ) )
        #with open( filepath, 'rb' ) as pickleFile:
        #    typicalAddedUnits = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it

        if BibleOrgSysGlobals.verbosityLevel > 2: print( t("Running discover on {}...").format( self.name ) )
        for BBB in self.books: # Do individual book prechecks
            if BibleOrgSysGlobals.verbosityLevel > 3: print( "  " + t("Prechecking {}...").format( BBB ) )
            self.books[BBB]._discover( self.discoveryResults )

        self._aggregateDiscoveryResults()
    # end of InternalBible.discover


    def _aggregateDiscoveryResults( self ):
        """
        Assuming that the individual discoveryResults have been collected for each book,
            puts them all together.
        """
        if BibleOrgSysGlobals.verbosityLevel > 0: print( "InternalBible:_aggregateDiscoveryResults()" )
        aggregateResults = {}
        if BibleOrgSysGlobals.debugFlag: assert( 'ALL' not in self.discoveryResults )
        for BBB in self.discoveryResults:
            #print( "discoveryResults for", BBB, len(self.discoveryResults[BBB]), self.discoveryResults[BBB] )
            isOT = isNT = isDC = False
            if BibleOrgSysGlobals.BibleBooksCodes.isOldTestament_NR( BBB ):
                isOT = True
                if 'OTBookCount' not in aggregateResults: aggregateResults['OTBookCount'], aggregateResults['OTBookCodes'] = 1, [BBB]
                else: aggregateResults['OTBookCount'] += 1; aggregateResults['OTBookCodes'].append( BBB )
            elif BibleOrgSysGlobals.BibleBooksCodes.isNewTestament_NR( BBB ):
                isNT = True
                if 'NTBookCount' not in aggregateResults: aggregateResults['NTBookCount'], aggregateResults['NTBookCodes'] = 1, [BBB]
                else: aggregateResults['NTBookCount'] += 1; aggregateResults['NTBookCodes'].append( BBB )
            elif BibleOrgSysGlobals.BibleBooksCodes.isDeuterocanon_NR( BBB ):
                isDC = True
                if 'DCBookCount' not in aggregateResults: aggregateResults['DCBookCount'], aggregateResults['DCBookCodes'] = 1, [BBB]
                else: aggregateResults['DCBookCount'] += 1; aggregateResults['DCBookCodes'].append( BBB )
            else: # not conventional OT or NT or DC
                if 'OtherBookCount' not in aggregateResults: aggregateResults['OtherBookCount'], aggregateResults['OtherBookCodes'] = 1, [BBB]
                else: aggregateResults['OtherBookCount'] += 1; aggregateResults['OtherBookCodes'].append( BBB )

            for key,value in self.discoveryResults[BBB].items():
                # Create some lists of books
                #if key == 'wordCount': print( BBB, key, value )
                if key=='notStarted' and value:
                    if 'NotStartedBookCodes' not in aggregateResults: aggregateResults['NotStartedBookCodes'] = [BBB]
                    else: aggregateResults['NotStartedBookCodes'].append( BBB )
                    if isOT:
                        if 'OTNotStartedBookCodes' not in aggregateResults: aggregateResults['OTNotStartedBookCodes'] = [BBB]
                        else: aggregateResults['OTNotStartedBookCodes'].append( BBB )
                    elif isNT:
                        if 'NTNotStartedBookCodes' not in aggregateResults: aggregateResults['NTNotStartedBookCodes'] = [BBB]
                        else: aggregateResults['NTNotStartedBookCodes'].append( BBB )
                    elif isDC:
                        if 'DCNotStartedBookCodes' not in aggregateResults: aggregateResults['DCNotStartedBookCodes'] = [BBB]
                        else: aggregateResults['DCNotStartedBookCodes'].append( BBB )
                elif key=='seemsFinished' and value:
                    if 'SeemsFinishedBookCodes' not in aggregateResults: aggregateResults['SeemsFinishedBookCodes'] = [BBB]
                    else: aggregateResults['SeemsFinishedBookCodes'].append( BBB )
                    if isOT:
                        if 'OTSeemsFinishedBookCodes' not in aggregateResults: aggregateResults['OTSeemsFinishedBookCodes'] = [BBB]
                        else: aggregateResults['OTSeemsFinishedBookCodes'].append( BBB )
                    elif isNT:
                        if 'NTSeemsFinishedBookCodes' not in aggregateResults: aggregateResults['NTSeemsFinishedBookCodes'] = [BBB]
                        else: aggregateResults['NTSeemsFinishedBookCodes'].append( BBB )
                    elif isDC:
                        if 'DCSeemsFinishedBookCodes' not in aggregateResults: aggregateResults['DCSeemsFinishedBookCodes'] = [BBB]
                        else: aggregateResults['DCSeemsFinishedBookCodes'].append( BBB )
                elif key=='partlyDone' and value:
                    if 'PartlyDoneBookCodes' not in aggregateResults: aggregateResults['PartlyDoneBookCodes'] = [BBB]
                    else: aggregateResults['PartlyDoneBookCodes'].append( BBB )
                    if isOT:
                        if 'OTPartlyDoneBookCodes' not in aggregateResults: aggregateResults['OTPartlyDoneBookCodes'] = [BBB]
                        else: aggregateResults['OTPartlyDoneBookCodes'].append( BBB )
                    elif isNT:
                        if 'NTPartlyDoneBookCodes' not in aggregateResults: aggregateResults['NTPartlyDoneBookCodes'] = [BBB]
                        else: aggregateResults['NTPartlyDoneBookCodes'].append( BBB )
                    elif isDC:
                        if 'DCPartlyDoneBookCodes' not in aggregateResults: aggregateResults['DCPartlyDoneBookCodes'] = [BBB]
                        else: aggregateResults['DCPartlyDoneBookCodes'].append( BBB )

                # Aggregate book statistics into a whole
                if key == 'percentageProgress':
                    if 'percentageProgressByBook' not in aggregateResults: aggregateResults['percentageProgressByBook'] = value
                    else: aggregateResults['percentageProgressByBook'] += value
                    if isOT:
                        if 'OTpercentageProgressByBook' not in aggregateResults: aggregateResults['OTpercentageProgressByBook'] = value
                        else: aggregateResults['OTpercentageProgressByBook'] += value
                    elif isNT:
                        if 'NTpercentageProgressByBook' not in aggregateResults: aggregateResults['NTpercentageProgressByBook'] = value
                        else: aggregateResults['NTpercentageProgressByBook'] += value
                    elif isDC:
                        if 'DCpercentageProgressByBook' not in aggregateResults: aggregateResults['DCpercentageProgressByBook'] = value
                        else: aggregateResults['DCpercentageProgressByBook'] += value
                    #print( 'xxx', value, aggregateResults['percentageProgressByBook'] )
                elif key == 'uniqueWordCount': pass # Makes no sense to aggregate this
                elif key.endswith( 'WordCounts' ): # We need to combine these word count dictionaries
                    #print( "wcGot", BBB, key )
                    if key not in aggregateResults: aggregateResults[key] = {}
                    assert( isinstance( value, dict ) )
                    for word in value:
                        assert( isinstance( word, str ) )
                        assert( isinstance( value[word], int ) )
                        if word not in aggregateResults[key]: aggregateResults[key][word] = 0
                        aggregateResults[key][word] += value[word]
                elif isinstance( value, float ): # e.g., crossReferencesPeriodRatio
                    #print( "fgot", BBB, key, value )
                    if 0.0 <= value <= 1.0:
                        if key not in aggregateResults: aggregateResults[key] = [value]
                        else: aggregateResults[key].append( value )
                    elif value != -1.0: logging.warning( t("discover: invalid ratio (float) {} {} {}").format( BBB, key, repr(value) ) )
                elif isinstance( value, int ): # e.g., completedVerseCount and also booleans such as havePopulatedCVmarkers
                    #print( "igot", BBB, key, value )
                    if key not in aggregateResults: aggregateResults[key] = value
                    else: aggregateResults[key] += value
                    if isOT:
                        if 'OT'+key not in aggregateResults: aggregateResults['OT'+key] = value
                        else: aggregateResults['OT'+key] += value
                    elif isNT:
                        if 'NT'+key not in aggregateResults: aggregateResults['NT'+key] = value
                        else: aggregateResults['NT'+key] += value
                    elif isDC:
                        if 'DC'+key not in aggregateResults: aggregateResults['DC'+key] = value
                        else: aggregateResults['DC'+key] += value
                    else: # front-back matter
                        if 'OTHER'+key not in aggregateResults: aggregateResults['OTHER'+key] = value
                        else: aggregateResults['OTHER'+key] += value
                #elif value==True: # This test must come below the isinstance tests
                    #print( "tgot", BBB, key, value ); halt
                    #if key not in aggregateResults: aggregateResults[key] = 1
                    #else: aggregateResults[key] += 1
                    #if isOT:
                        #if 'OT'+key not in aggregateResults: aggregateResults['OT'+key] = 1
                        #else: aggregateResults['OT'+key] += 1
                    #elif isNT:
                        #if 'NT'+key not in aggregateResults: aggregateResults['NT'+key] = 1
                        #else: aggregateResults['NT'+key] += 1
                    #elif isDC:
                        #if 'DC'+key not in aggregateResults: aggregateResults['DC'+key] = 1
                        #else: aggregateResults['DC'+key] += 1
                #elif value==False:
                    #halt
                    #pass # No action needed here
                else:
                    logging.warning( t("discover: unactioned discovery result {} {} {}").format( BBB, key, repr(value) ) )

        for arKey in list(aggregateResults.keys()): # Make a list first so we can delete entries later
            # Create summaries of lists with entries for various books
            #print( "check", arKey, aggregateResults[arKey] )
            if isinstance( aggregateResults[arKey], list ) and isinstance( aggregateResults[arKey][0], float ):
                if BibleOrgSysGlobals.debugFlag: assert( arKey.endswith( 'Ratio' ) )
                #print( "this", arKey, aggregateResults[arKey] )
                aggregateRatio = round( sum( aggregateResults[arKey] ) / len( aggregateResults[arKey] ), 2 )
                aggregateFlag = None
                if aggregateRatio > 0.6: aggregateFlag = True
                if aggregateRatio < 0.4: aggregateFlag = False
                #print( "now", arKey, aggregateResults[arKey] )
                del aggregateResults[arKey] # Get rid of the ratio
                aggregateResults[arKey[:-5]+'Flag'] = aggregateFlag

        # Now calculate our overall statistics
        #print( "pre-aggregateResults", len(self), len(aggregateResults), aggregateResults )
        if 'percentageProgressByBook' in aggregateResults:
            aggregateResults['percentageProgressByBook'] = str( round( aggregateResults['percentageProgressByBook'] / len(self) ) ) + '%'
        if 'OTpercentageProgressByBook' in aggregateResults:
            aggregateResults['OTpercentageProgressByBook'] = str( round( aggregateResults['OTpercentageProgressByBook'] / 39 ) ) + '%'
        if 'NTpercentageProgressByBook' in aggregateResults:
            aggregateResults['NTpercentageProgressByBook'] = str( round( aggregateResults['NTpercentageProgressByBook'] / 27 ) ) + '%'
        if 'DCpercentageProgressByBook' in aggregateResults:
            aggregateResults['DCpercentageProgressByBook'] = str( round( aggregateResults['DCpercentageProgressByBook'] / 15 ) ) + '%'
        if 'completedVerseCount' in aggregateResults and 'verseCount' in aggregateResults:
            aggregateResults['percentageProgressByVerse'] = str( round( aggregateResults['completedVerseCount'] * 100 / aggregateResults['verseCount'] ) ) + '%'
        if 'OTcompletedVerseCount' in aggregateResults and 'OTverseCount' in aggregateResults:
            aggregateResults['OTpercentageProgressByVerse'] = str( round( aggregateResults['OTcompletedVerseCount'] * 100 / aggregateResults['OTverseCount'] ) ) + '%'
        if 'NTcompletedVerseCount' in aggregateResults and 'NTverseCount' in aggregateResults:
            aggregateResults['NTpercentageProgressByVerse'] = str( round( aggregateResults['NTcompletedVerseCount'] * 100 / aggregateResults['NTverseCount'] ) ) + '%'
        if 'DCcompletedVerseCount' in aggregateResults and 'DCverseCount' in aggregateResults:
            aggregateResults['DCpercentageProgressByVerse'] = str( round( aggregateResults['DCcompletedVerseCount'] * 100 / aggregateResults['DCverseCount'] ) ) + '%'

        # Save the results
        #print( "ALL discoveryResults", aggregateResults ); halt
        #for key,value in aggregateResults.items():
            #if key.endswith( 'ordCount' ): print( key, value )
        self.discoveryResults['ALL'] = aggregateResults

        if BibleOrgSysGlobals.verbosityLevel > 2: # or self.name=="Matigsalug": # Display some of these results
            print( "Discovered Bible parameters:" )
            if BibleOrgSysGlobals.verbosityLevel > 2: # or self.name=="Matigsalug": # Print completion level for each book
                for BBB in self.discoveryResults:
                    if BBB != 'ALL':
                        if 'seemsFinished' in self.discoveryResults[BBB] and self.discoveryResults[BBB]['seemsFinished']:
                            print( "   ", BBB, 'seems finished' ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        elif not self.discoveryResults[BBB]['haveVerseText']:
                            print( "   ", BBB, 'not started' ) #, str(self.discoveryResults[BBB]['percentageProgress'])+'%' )
                        else: print( "   ", BBB, 'in progress', (str(self.discoveryResults[BBB]['percentageProgress'])+'%') if 'percentageProgress' in self.discoveryResults[BBB] else '' )
            for key,value in sorted(self.discoveryResults['ALL'].items()):
                if 'percentage' in key or key.endswith('Count') or key.endswith('Flag') or key.endswith('Codes'):
                    print( " ", key, "is", value )
                elif key.endswith( 'WordCounts' ): pass # ignore these
                else:
                    #print( "key", repr(key), "value", repr(value) )
                    print( " ", key, "in", value if value<len(self) else "all", "books" )
    # end of InternalBible._aggregateDiscoveryResults


    def check( self, givenBookList=None ):
        """
        Runs self.discover() first if necessary.

        By default, runs a series of individual checks (and counts) on each book of the Bible
            and then a number of overall checks on the entire Bible.

        If a book list is given, only checks those books.

        getErrors() must be called to request the results.
        """
        # Get our recommendations for added units -- only load this once per Bible
        if BibleOrgSysGlobals.verbosityLevel > 1:
            if givenBookList is None: print( t("Checking {} Bible...").format( self.name ) )
            else: print( t("Checking {} Bible books {}...").format( self.name, givenBookList ) )
        if 'discoveryResults' not in dir(self): self.discover()

        import pickle
        pickleFolder = os.path.join( os.path.dirname(__file__), "DataFiles/", "ScrapedFiles/" ) # Relative to module, not cwd
        pickleFilepath = os.path.join( pickleFolder, "AddedUnitData.pickle" )
        if BibleOrgSysGlobals.verbosityLevel > 3: print( t("Importing from {}...").format( pickleFilepath ) )
        with open( pickleFilepath, 'rb' ) as pickleFile:
            typicalAddedUnitData = pickle.load( pickleFile ) # The protocol version used is detected automatically, so we do not have to specify it

        if BibleOrgSysGlobals.debugFlag: assert( self.discoveryResults )
        if BibleOrgSysGlobals.verbosityLevel > 2: print( t("Running checks on {}...").format( self.name ) )
        if givenBookList is None:
            givenBookList = self.books # this is an OrderedDict
        for BBB in givenBookList: # Do individual book checks
            if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + t("Checking {}...").format( BBB ) )
            self.books[BBB].check( self.discoveryResults['ALL'], typicalAddedUnitData )

        # Do overall Bible checks here
        # xxxxxxxxxxxxxxxxx ......................................
    # end of InternalBible.check


    def getErrors( self, givenBookList=None ):
        """
        Returns the error dictionary.
            All keys ending in 'Errors' give lists of strings.
            All keys ending in 'Counts' give OrderedDicts with [value]:count entries
            All other keys give subkeys
            The structure is:
                errors: OrderedDict
                    ['ByBook']: OrderedDict
                        ['All Books']: OrderedDict
                        [BBB] in order: OrderedDict
                            ['Priority Errors']: list
                            ['Load Errors']: list
                            ['Fix Text Errors']: list
                            ['Versification Errors']: list
                            ['SFMs']: OrderedDict
                                ['Newline Marker Errors']: list
                                ['Internal Marker Errors']: list
                                ['All Newline Marker Counts']: OrderedDict
                            ['Characters']: OrderedDict
                                ['All Character Counts']: OrderedDict
                                ['Letter Counts']: OrderedDict
                                ['Punctuation Counts']: OrderedDict
                            ['Words']: OrderedDict
                                ['All Word Counts']: OrderedDict
                                ['Case Insensitive Word Counts']: OrderedDict
                            ['Headings']: OrderedDict
                    ['ByCategory']: OrderedDict
        """
        if givenBookList is None: givenBookList = self.books # this is an OrderedDict

        def appendList( BBB, errorDict, firstKey, secondKey=None ):
            """Appends a list to the ALL BOOKS errors."""
            #print( "  appendList", BBB, firstKey, secondKey )
            if secondKey is None:
                if BibleOrgSysGlobals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], list ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = []
                errorDict['All Books'][firstKey].extend( errorDict[BBB][firstKey] )
            else: # We have an extra level
                if BibleOrgSysGlobals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], dict ) )
                if BibleOrgSysGlobals.debugFlag: assert( isinstance (errorDict[BBB][firstKey][secondKey], list ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = OrderedDict()
                if secondKey not in errorDict['All Books'][firstKey]: errorDict['All Books'][firstKey][secondKey] = []
                errorDict['All Books'][firstKey][secondKey].extend( errorDict[BBB][firstKey][secondKey] )
        # end of getErrors.appendList

        def mergeCount( BBB, errorDict, firstKey, secondKey=None ):
            """Merges the counts together."""
            #print( "  mergeCount", BBB, firstKey, secondKey )
            if secondKey is None:
                if BibleOrgSysGlobals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], dict ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = {}
                for something in errorDict[BBB][firstKey]:
                    errorDict['All Books'][firstKey][something] = 1 if something not in errorDict['All Books'][firstKey] else errorDict[BBB][firstKey][something] + 1
            else:
                if BibleOrgSysGlobals.debugFlag: assert( isinstance (errorDict[BBB][firstKey], (dict, OrderedDict,) ) )
                if BibleOrgSysGlobals.debugFlag: assert( isinstance (errorDict[BBB][firstKey][secondKey], dict ) )
                if firstKey not in errorDict['All Books']: errorDict['All Books'][firstKey] = OrderedDict()
                if secondKey not in errorDict['All Books'][firstKey]: errorDict['All Books'][firstKey][secondKey] = {}
                for something in errorDict[BBB][firstKey][secondKey]:
                    errorDict['All Books'][firstKey][secondKey][something] = errorDict[BBB][firstKey][secondKey][something] if something not in errorDict['All Books'][firstKey][secondKey] \
                                                                                else errorDict['All Books'][firstKey][secondKey][something] + errorDict[BBB][firstKey][secondKey][something]
        # end of getErrors.mergeCount

        def getCapsList( lcWord, lcTotal, wordDict ):
            """ Given that a lower case word has a lowercase count of lcTotal,
                search wordDict to find all the ways that it occurs
                and return this as a list sorted with the most frequent first."""
            tempResult = []

            lcCount = wordDict[lcWord] if lcWord in wordDict else 0
            if lcCount: tempResult.append( (lcCount,lcWord,) )
            total = lcCount

            if total < lcTotal:
                tcWord = lcWord.title() # NOTE: This can make in-enew into In-Enew
                if BibleOrgSysGlobals.debugFlag: assert( tcWord != lcWord )
                tcCount = wordDict[tcWord] if tcWord in wordDict else 0
                if tcCount: tempResult.append( (tcCount,tcWord,) ); total += tcCount
            if total < lcTotal:
                TcWord = lcWord[0].upper() + lcWord[1:] # NOTE: This can make in-enew into In-enew
                #print( lcWord, tcWord, TcWord )
                #assert( TcWord != lcWord )
                if TcWord!=lcWord and TcWord!=tcWord: # The first two can be equal if the first char is non-alphabetic
                    TcCount = wordDict[TcWord] if TcWord in wordDict else 0
                    if TcCount: tempResult.append( (TcCount,TcWord,) ); total += TcCount
            if total < lcTotal:
                tCWord = tcWord[0].lower() + tcWord[1:] # NOTE: This can make Matig-Kurintu into matig-Kurintu (but won't change 1Cor)
                if tCWord!=lcWord and tCWord!=tcWord and tCWord!=TcWord:
                    tCCount = wordDict[tCWord] if tCWord in wordDict else 0
                    if tCCount: tempResult.append( (tCCount,tCWord,) ); total += tCCount
            if total < lcTotal:
                UCWord = lcWord.upper()
                if BibleOrgSysGlobals.debugFlag: assert( UCWord!=lcWord )
                if UCWord != TcWord:
                    UCCount = wordDict[UCWord] if UCWord in wordDict else 0
                    if UCCount: tempResult.append( (UCCount,UCWord,) ); total += UCCount
            if total < lcTotal: # There's only one (slow) way left -- look at every word
                for word in wordDict:
                    if word.lower()==lcWord and word not in ( lcWord, tcWord, TcWord, tCWord, UCWord ):
                        tempResult.append( (wordDict[word],word,) ); total += wordDict[word]
                        # Seems we don't know the BCV reference here unfortunately
                        if 'Possible Word Errors' not in errors['ByBook']['All Books']['Words']: errors['ByBook']['All Books']['Words']['Possible Word Errors'] = []
                        errors['ByBook']['All Books']['Words']['Possible Word Errors'].append( _("Word {!r} appears to have unusual capitalization").format( word ) )
                        if total == lcTotal: break # no more to find

            if total < lcTotal:
                print( "Couldn't get word total with", lcWord, lcTotal, total, tempResult )
                print( lcWord, tcWord, TcWord, tCWord, UCWord )

            result = [w for c,w in sorted(tempResult)]
            #if len(tempResult)>2: print( lcWord, lcTotal, total, tempResult, result )
            return result
        # end of getErrors.getCapsList

        # Set up
        errors = OrderedDict(); errors['ByBook'] = OrderedDict(); errors['ByCategory'] = OrderedDict()
        for category in ('Priority Errors','Load Errors','Fix Text Errors','Validation Errors','Versification Errors',):
            errors['ByCategory'][category] = [] # get these in a logical order (remember: they might not all occur for each book)
        for category in ('SFMs','Characters','Words','Headings','Introduction','Notes','Controls',): # get these in a logical order
            errors['ByCategory'][category] = OrderedDict()
        errors['ByBook']['All Books'] = OrderedDict()

        # Make sure that the error lists come first in the All Books ordered dictionaries (even if there's no errors for the first book)
        for BBB in self.books.keys():
            if BBB in givenBookList:
                errors['ByBook'][BBB] = self.books[BBB].getErrors()
                for thisKey in errors['ByBook'][BBB]:
                    if thisKey.endswith('Errors'):
                        errors['ByBook']['All Books'][thisKey] = []
                        errors['ByCategory'][thisKey] = []
                    elif not thisKey.endswith('List') and not thisKey.endswith('Lines'):
                        for anotherKey in errors['ByBook'][BBB][thisKey]:
                            if anotherKey.endswith('Errors'):
                                if thisKey not in errors['ByBook']['All Books']: errors['ByBook']['All Books'][thisKey] = OrderedDict()
                                errors['ByBook']['All Books'][thisKey][anotherKey] = []
                                if thisKey not in errors['ByCategory']: errors['ByCategory'][thisKey] = OrderedDict()
                                errors['ByCategory'][thisKey][anotherKey] = []

        # Combine book errors into Bible totals plus into categories
        for BBB in self.books.keys():
            if BBB in givenBookList:
                #errors['ByBook'][BBB] = self.books[BBB].getErrors()

                # Correlate some of the totals (i.e., combine book totals into Bible totals)
                # Also, create a dictionary of errors by category (as well as the main one by book reference code BBB)
                for thisKey in errors['ByBook'][BBB]:
                    #print( "thisKey", BBB, thisKey )
                    if thisKey.endswith('Errors') or thisKey.endswith('List') or thisKey.endswith('Lines'):
                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( errors['ByBook'][BBB][thisKey], list ) )
                        appendList( BBB, errors['ByBook'], thisKey )
                        errors['ByCategory'][thisKey].extend( errors['ByBook'][BBB][thisKey] )
                    elif thisKey.endswith('Counts'):
                        NEVER_HAPPENS # does this happen?
                        mergeCount( BBB, errors['ByBook'], thisKey )
                    else: # it's things like SFMs, Characters, Words, Headings, Notes
                        for anotherKey in errors['ByBook'][BBB][thisKey]:
                            #print( " anotherKey", BBB, anotherKey )
                            if anotherKey.endswith('Errors') or anotherKey.endswith('List') or anotherKey.endswith('Lines'):
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( errors['ByBook'][BBB][thisKey][anotherKey], list ) )
                                appendList( BBB, errors['ByBook'], thisKey, anotherKey )
                                if thisKey not in errors['ByCategory']: errors['ByCategory'][thisKey] = OrderedDict() #; print( "Added", thisKey )
                                if anotherKey not in errors['ByCategory'][thisKey]: errors['ByCategory'][thisKey][anotherKey] = []
                                errors['ByCategory'][thisKey][anotherKey].extend( errors['ByBook'][BBB][thisKey][anotherKey] )
                            elif anotherKey.endswith('Counts'):
                                mergeCount( BBB, errors['ByBook'], thisKey, anotherKey )
                                # Haven't put counts into category array yet
                            else:
                                print( anotherKey, "not done yet" )
                                #halt # Not done yet

        # Taking those word lists, find uncommon words
        threshold = 4 # i.e., find words used less often that this many times as possible candidates for spelling errors
        uncommonWordCounts = {}
        if 'Words' in errors['ByBook']['All Books']:
            for word, lcCount in errors['ByBook']['All Books']['Words']['Case Insensitive Word Counts'].items():
                adjWord = word
                if word not in errors['ByBook']['All Books']['Words']['All Word Counts'] \
                or errors['ByBook']['All Books']['Words']['All Word Counts'][word] < lcCount: # then it sometimes occurs capitalized in some way
                    # Look for uncommon capitalizations
                    results = getCapsList( word, lcCount, errors['ByBook']['All Books']['Words']['All Word Counts'] )
                    if len(results) > 2:
                        if 'Possible Word Errors' not in errors['ByBook']['All Books']['Words']: errors['ByBook']['All Books']['Words']['Possible Word Errors'] = []
                        errors['ByBook']['All Books']['Words']['Possible Word Errors'].append( _("Lots of ways of capitalizing {}").format( results ) )
                if lcCount < threshold: # look for uncommon words
                    if word not in errors['ByBook']['All Books']['Words']['All Word Counts']: # then it ONLY occurs capitalized in some way
                        adjWord = getCapsList( word, lcCount, errors['ByBook']['All Books']['Words']['All Word Counts'] )[0]
                    uncommonWordCounts[adjWord] = lcCount
            if uncommonWordCounts: errors['ByBook']['All Books']['Words']['Uncommon Word Counts'] = uncommonWordCounts

    	# Remove any unnecessary empty categories
        for category in errors['ByCategory']:
            if not errors['ByCategory'][category]:
                #print( "InternalBible.getErrors: Removing empty category", category, "from errors['ByCategory']" )
                del errors['ByCategory'][category]
        return errors
    # end of InternalBible.getErrors


    def makeErrorHTML( self, givenOutputFolder, givenBookList=None, titlePrefix=None, webPageTemplate=None ):
        """
        Gets the error dictionaries that were the result of the check
            and produce linked HTML pages in the given output folder.

        All pages are built with relative links.

        Returns the path to the index.html file
            or None if there was a problem.
        """
        from datetime import datetime
        if BibleOrgSysGlobals.debugFlag:
            print( "makeErrorHTML( {}, {}, {} )" \
                .format( repr(givenOutputFolder), repr(titlePrefix), repr(webPageTemplate) ) )
        #logging.info( "Doing Bible checks..." )
        #if BibleOrgSysGlobals.verbosityLevel > 2: print( "Doing Bible checks..." )

        errorDictionary = self.getErrors( givenBookList )
        if givenBookList is None: givenBookList = self.books # this is an OrderedDict

        if webPageTemplate is None:
            webPageTemplate = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="content-type" content="text/html;charset=UTF-8"/>
<link rel="stylesheet" href="__TOP_PATH__Overall.css" type="text/css"/>
    <title>__TITLE__</title>
</head>

<body class="HTMLBody">
<div id="TopBar"><a href="__TOP_PATH__"><img class="Banner" height="120" src="__TOP_PATH__Logo/FG-Banner.jpg" alt="Top logo banner graphic"/></a>
    <h1 class="PageHeading">__HEADING__</h1></div>
<div id="MainContent">
<div id="LeftSidebar">
    <p>
    <br /><a href="__TOP_PATH__index.html">Checks</a>
    </p></div>

<div id="MainSection">
    __MAIN_PART__
    </div>
</div>

<div id="Footer">
    <p class="GeneratedNotice">This page automatically generated __DATE__ from a template created 2014-11-23</p>
    </p></div>
</body></html>
"""
        webPageTemplate = webPageTemplate.replace( '__DATE__', datetime.now().strftime('%Y-%m-%d') )

        defaultTopPath = ""

        # Make our own output folder
        outputFolder = os.path.join( givenOutputFolder, 'BOS_Check_Results/' )
        try: os.mkdir( outputFolder, 0o755 )
        except FileExistsError: pass # Must be redoing it
        pagesFolder = os.path.join( outputFolder, 'Pages/' )
        try: os.mkdir( pagesFolder, 0o755 )
        except FileExistsError: pass # Must be redoing it

        ourTitle = _("Bible Checks")
        if titlePrefix is None: titlePrefix = self.abbreviation
        if titlePrefix: ourTitle = titlePrefix + ' ' + ourTitle

        if not errorDictionary: indexPart = "<p>No Bible errors found.</p>"
        else:
            BBBIndexPart, categoryIndexPart = "", ""
            BBBIndexPart += '<table>'
            if len(errorDictionary['ByBook']) < 3: # Assume there's only one BBB book, plus 'All Books'
                del errorDictionary['ByBook']['All Books']
            for BBB in errorDictionary['ByBook']: # Create an error page for each book (and for all books if there's more than one book)
                #print( "Have errors for", BBB )
                if not errorDictionary['ByBook'][BBB]: # Then it's blank
                    print( "HEY 0—Should not have had blank entry for", BBB )
                BBBPart = ""
                for thisKey in errorDictionary['ByBook'][BBB]:
                    if BibleOrgSysGlobals.debugFlag: assert( isinstance( thisKey, str ) )
                    if not errorDictionary['ByBook'][BBB][thisKey]: print( "HEY 1—Should not have had", BBB, thisKey )
                    #print( 'ByBook', BBB, thisKey )
                    if errorDictionary['ByBook'][BBB][thisKey]:
                        BBBPart += "<h1>{}</h1>".format( thisKey )
                        if thisKey == 'Priority Errors': # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey], list ) )
                            count, lastError, lastBk, lastCh, lastVs = 0, '', '', '', ''
                            #for priority,errorText,ref in sorted( errorDictionary['ByBook'][BBB][thisKey], reverse=True ): # Sorts by the first tuple value which is priority
                            for priority,errorText,ref in sorted( errorDictionary['ByBook'][BBB][thisKey], key=lambda theTuple: theTuple[0], reverse=True ): # Sorts by the first tuple value which is priority
                            #for priority,errorText,ref in errorDictionary['ByBook'][BBB][thisKey]: # Sorts by the first tuple value which is priority
                                #print( 'BBB', priority,errorText,ref )
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( priority, int ) and 0 <= priority <= 100 )
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorText, str ) and errorText )
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( ref, tuple ) and len(ref)==3 )
                                bk, ch, vs = ref
                                if errorText != lastError:
                                    if count: BBBPart += '</p>'
                                    BBBPart += "<p>{} in {} {}:{}".format( errorText, bk, ch, vs )
                                    count += 1
                                elif bk and bk!=lastBk: BBBPart += "; {} {}:{}".format( bk, ch, vs )
                                elif ch and ch!=lastCh: BBBPart += "; {}:{}".format( ch, vs )
                                elif vs and vs!=lastVs: BBBPart += ",{}".format( vs )
                                if count>=20 or priority<30:
                                    BBBPart += "</p><p><small>Showing {} out of {} priority errors</small></p>".format( count, len(errorDictionary['ByBook'][BBB][thisKey]) )
                                    break
                                if bk: lastBk = bk
                                if ch: lastCh = ch
                                if vs: lastVs = vs
                                lastError = errorText
                        elif thisKey.endswith('Errors'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey], list ) )
                            for error in errorDictionary['ByBook'][BBB][thisKey]:
                                #print( "nice1", 'ByBook', BBB, thisKey, error )
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                                BBBPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('List'): # it should be a list
                            NEVER_HAPPENS
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey], list ) )
                            BBBPart += "<h1>{}</h1>".format( thisKey )
                            for error in errorDictionary['ByBook'][BBB][thisKey]:
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                                BBBPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('Lines'): # it should be a list
                            NEVER_HAPPENS
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey], list ) )
                        elif thisKey.endswith('Counts'): # it should be an ordered dict
                            NEVER_HAPPENS
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey], (dict, OrderedDict,) ) )
                            for subCategory in errorDictionary['ByBook'][BBB][thisKey]:
                                #print( "subCategory1", subCategory )
                                if subCategory.endswith('Errors'):
                                    BBBPart += "<h2>{}</h2>".format( subCategory )
                                    for error in errorDictionary['ByBook'][BBB][thisKey][subCategory]:
                                        BBBPart += "<p>{}</p>".format( error )
                                elif subCategory.endswith('Counts'):
                                    BBBPart += "<h2>{}</h2>".format( subCategory ) + "<p>"
                                    for something in sorted(errorDictionary['ByBook'][BBB][thisKey][subCategory]):
                                        BBBPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, errorDictionary['ByBook'][BBB][thisKey][subCategory][something] )
                                    BBBPart += "</p>"
                                else: print( "A weird 1" ); halt
                        else: # Have a category with subcategories
                            for secondKey in errorDictionary['ByBook'][BBB][thisKey]:
                                if not errorDictionary['ByBook'][BBB][thisKey][secondKey]: print( "HEY 3—Should not have had", BBB, thisKey, secondKey )
                                if errorDictionary['ByBook'][BBB][thisKey][secondKey]:
                                    if secondKey.endswith('Errors'): # it should be a list
                                        #print( "BBB Have ..Errors", BBB, thisKey, secondKey )
                                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], list ) )
                                        BBBPart += "<h2>{}</h2>".format( secondKey )
                                        for error in errorDictionary['ByBook'][BBB][thisKey][secondKey]:
                                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                                            BBBPart += "<p>{}</p>".format( error )
                                    elif secondKey.endswith('List'): # it should be a list
                                        #print( "BBB Have ..List", BBB, thisKey, secondKey, len(errorDictionary['ByBook'][BBB][thisKey][secondKey]), len(errorDictionary['ByBook'][BBB][thisKey][secondKey][0]) )
                                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], list ) )
                                        if secondKey == "Modified Marker List" and len(errorDictionary['ByBook'][BBB][thisKey][secondKey])>60: # Put onto a separate page
                                            ListPart = '<p>'
                                            for jj,entry in enumerate( errorDictionary['ByBook'][BBB][thisKey][secondKey] ):
                                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( entry, str ) )
                                                if thisKey=='USFMs' and secondKey=='Modified Marker List' and entry[0]=='[' and entry[-1]==']':
                                                    if BBB!='All Books': continue # Don't display the BBB book reference code
                                                    if BBB=='All Books' and jj: ListPart += "</p>\n<p>" # Start each new book on a new line
                                                ListPart += "{} ".format( entry )
                                            ListPart += '</p>'
                                            webPage = webPageTemplate.replace( "__TITLE__", ourTitle+" USFM {}".format(secondKey) ).replace( "__HEADING__", ourTitle+" USFM Bible {}".format(secondKey) ) \
                                                        .replace( "__MAIN_PART__", ListPart ).replace( "__EXTRAS__", '' ) \
                                                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                                        #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
                                            webPageFilename = "{}_{}.html".format( BBB, secondKey.replace(' ','') )
                                            with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                                                myFile.write( webPage )
                                            BBBPart += '<p><a href="{}">{}</a></p>'.format( webPageFilename, secondKey )
                                        else: # Just show it inline
                                            BBBPart += "<h2>{}</h2><p>".format( secondKey )
                                            for jj,entry in enumerate( errorDictionary['ByBook'][BBB][thisKey][secondKey] ):
                                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( entry, str ) )
                                                if thisKey=='USFMs' and secondKey=='Modified Marker List' and entry[0]=='[' and entry[-1]==']':
                                                    if BBB!='All Books': continue # Don't display the BBB book reference code
                                                    if BBB=='All Books' and jj: BBBPart += "</p>\n<p>" # Start each new book on a new line
                                                BBBPart += "{} ".format( entry )
                                            BBBPart += '</p>'
                                    elif secondKey.endswith('Lines'): # it should be a list
                                        #print( "BBB Have ..Lines", BBB, thisKey, secondKey )
                                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], list ) )
                                        BBBPart += "<h2>{}</h2><table>".format( secondKey )
                                        for line in errorDictionary['ByBook'][BBB][thisKey][secondKey]: # Line them up nicely in a table
                                            #print( "line {} {!r}".format( len(line), line ) )
                                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( line, str ) and line[-1]=="'" )
                                            #if line[-1] != "'": print( BBB, thisKey, secondKey, line )
                                            bits = line[:-1].split( " '", 1 ); assert( len(bits) == 2 ) # Remove the final quote and split at the first quote
                                            if "Main Title 1" in bits[0]: bits[1] = "<b>" + bits[1] + "</b>"
                                            BBBPart += "<tr><td>{}</td><td>{}</td></tr>".format( bits[0], bits[1] ) # Put in a table row
                                        BBBPart += '</table>'
                                    elif secondKey.endswith('Counts'): # it should be an ordered dict
                                        #print( "BBB Have ..Counts", BBB, thisKey, secondKey )
                                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByBook'][BBB][thisKey][secondKey], (dict, OrderedDict,) ) )
                                        if len(errorDictionary['ByBook'][BBB][thisKey][secondKey]) < 50: # Small list -- just include it in this page
                                            BBBPart += "<h2>{}</h2>".format( secondKey ) + "<p>"
                                            for something, count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[0].lower() ): # Sort by lower-case values
                                                BBBPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            BBBPart += "</p>"
                                            BBBPart += "<h2>{} (sorted by count)</h2>".format( secondKey ) + "<p>"
                                            for something, count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[1] ): # Sort by count
                                                BBBPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            BBBPart += "</p>"
                                        else: # Large list of counts -- put it on a separate page
                                            CountPart = ''
                                            for something,count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[0].lower() ): # Sort by lower-case values
                                                CountPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            webPage = webPageTemplate.replace( "__TITLE__", ourTitle+" USFM {}".format(secondKey) ).replace( "__HEADING__", ourTitle+" USFM Bible {}".format(secondKey) ) \
                                                        .replace( "__MAIN_PART__", CountPart ).replace( "__EXTRAS__", '' ) \
                                                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                                        #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
                                            webPageFilename = "{}_{}.html".format( BBB, secondKey.replace(' ','') )
                                            with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                                                myFile.write( webPage )
                                            BBBPart += '<p><a href="{}">{}</a></p>'.format( webPageFilename, secondKey )
                                            CountPart = ''
                                            for something,count in sorted( errorDictionary['ByBook'][BBB][thisKey][secondKey].items(), key=lambda theTuple: theTuple[1] ): # Sort by count
                                                CountPart += "&nbsp;<b>{}</b>:&nbsp;{}&nbsp;&nbsp; ".format( something, count )
                                            webPage = webPageTemplate.replace( "__TITLE__", ourTitle+" USFM {}".format(secondKey) ).replace( "__HEADING__", ourTitle+" USFM Bible {}".format(secondKey) ) \
                                                        .replace( "__MAIN_PART__", CountPart ).replace( "__EXTRAS__", '' ) \
                                                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                                        #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
                                            webPageFilename = "{}_{}_byCount.html".format( BBB, secondKey.replace(' ','') )
                                            with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                                                myFile.write( webPage )
                                            BBBPart += '<p><a href="{}">{} (sorted by count)</a></p>'.format( webPageFilename, secondKey )
                                    else: raise KeyError
                if BBBPart: # Create the error page for this book
                    webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle+" USFM Bible {} Checks".format(BBB) ) \
                                .replace( "__MAIN_PART__", BBBPart ).replace( "__EXTRAS__", '' ) \
                                .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
                    webPageFilename = "{}.html".format( BBB )
                    with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                        myFile.write( webPage )
                    #BBBIndexPart += '<p>Errors for book <a href="{}">{}</a></p>'.format( webPageFilename, BBB )
                    if BBB == 'All Books': BBBIndexPart += '<tr><td><a href="{}">ALL</a></td><td>All Books</td></tr>'.format( webPageFilename )
                    else: BBBIndexPart += '<tr><td><a href="{}">{}</a></td><td>{}</td></tr>'.format( webPageFilename, BBB, self.getAssumedBookName(BBB) )
            BBBIndexPart += '</table>'
            categoryIndexPart += '<table>'
            for category in errorDictionary['ByCategory']: # Create an error page for each book (and for all books)
                if not errorDictionary['ByCategory'][category]: print( "HEY 2—Should not have had", category )
                #print( "ProcessUSFMUploads.makeErrorHTML: Processing category", category, "..." )
                categoryPart = ""
                categoryPart += "<h1>{}</h1>".format( category )
                if category == 'Priority Errors': # it should be a list
                    if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByCategory'][category], list ) )
                    count, lastError, lastBk, lastCh, lastVs = 0, '', '', '', ''
                    #for priority,errorText,ref in sorted( errorDictionary['ByCategory'][category], reverse=True ): # Sorts by the first tuple value which is priority
                    for priority,errorText,ref in sorted( errorDictionary['ByCategory'][category], key=lambda theTuple: theTuple[0], reverse=True ): # Sorts by the first tuple value which is priority
                    #for priority,errorText,ref in errorDictionary['ByCategory'][category]: # Sorts by the first tuple value which is priority
                        #print( 'cat', priority,errorText,ref )
                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( priority, int ) and 0 <= priority <= 100 )
                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorText, str ) and errorText )
                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( ref, tuple ) and len(ref)==3 )
                        bk, ch, vs = ref
                        if errorText != lastError:
                            if count: categoryPart += '</p>'
                            categoryPart += "<p>{} in {} {}:{}".format( errorText, bk, ch, vs )
                            count += 1
                        elif bk and bk!=lastBk: categoryPart += "; {} {}:{}".format( bk, ch, vs )
                        elif ch and ch!=lastCh: categoryPart += "; {}:{}".format( ch, vs )
                        elif vs and vs!=lastVs: categoryPart += ",{}".format( vs )
                        if count>=50:
                            categoryPart += "</p><p><small>Showing {} out of {} priority errors</small></p>".format( count, len(errorDictionary['ByCategory'][category]) )
                            break
                        if bk: lastBk = bk
                        if ch: lastCh = ch
                        if vs: lastVs = vs
                        lastError = errorText
                elif category.endswith('Errors'): # it should be a list
                    if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByCategory'][category], list ) )
                    for error in errorDictionary['ByCategory'][category]:
                        if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                        categoryPart += "<p>{}</p>".format( error )
                elif category.endswith('Counts'): # it should be an ordered dict
                    NEVER_HAPPENS
                    for thisKey in errorDictionary['ByCategory'][category]:
                        if thisKey.endswith('Errors'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByCategory'][category][thisKey], list ) )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            for error in errorDictionary['ByCategory'][category][thisKey]:
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                                categoryPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('Counts'): # it should be a list
                            print( "Counts key", thisKey )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            if isinstance( errorDictionary['ByCategory'][category][thisKey], list ): # always true
                            #    for error in errorDictionary['ByCategory'][category][thisKey]:
                            #        if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                            #        categoryPart += "<p>{}</p>".format( error )
                            #elif isinstance( errorDictionary['ByCategory'][category][thisKey], (dict, OrderedDict,) ):
                                for subCategory in errorDictionary['ByCategory'][category][thisKey]:
                                    #print( subCategory )
                                    if subCategory.endswith('Errors'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory )
                                        for error in errorDictionary['ByCategory'][category][BBB][subCategory]:
                                            categoryPart += "<p>{}</p>".format( error )
                                    elif subCategory.endswith('Counts'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory ) + "<p>"
                                        for something in sorted(errorDictionary['ByCategory'][category][BBB][subCategory]):
                                            categoryPart += "{}:{} ".format( something, errorDictionary['ByCategory'][category][BBB][subCategory][something] )
                                        categoryPart += "</p>"
                                    else: print( "A weird 2" ); halt
                        else:
                            print( "Have left-over thisKey", thisKey )
                            continue # ignore for now temp ....................................................................
                            raise KeyError# it wasn't a list or a dictionary
                else: # it's a subcategory
                    for thisKey in errorDictionary['ByCategory'][category]:
                        if thisKey.endswith('Errors'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByCategory'][category][thisKey], list ) )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            for error in errorDictionary['ByCategory'][category][thisKey]:
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                                categoryPart += "<p>{}</p>".format( error )
                        elif thisKey.endswith('List'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByCategory'][category][thisKey], list ) )
                            categoryPart += "<h2>{}</h2><p>".format( thisKey )
                            for jj,entry in enumerate( errorDictionary['ByCategory'][category][thisKey] ):
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( entry, str ) )
                                if thisKey=='Modified Marker List' and entry[0]=='[' and entry[-1]==']' and jj:
                                    categoryPart += "</p>\n<p>" # Start each new book on a new line
                                categoryPart += "{} ".format( entry )
                            categoryPart += '</p>'
                        elif thisKey.endswith('Lines'): # it should be a list
                            if BibleOrgSysGlobals.debugFlag: assert( isinstance( errorDictionary['ByCategory'][category][thisKey], list ) )
                            categoryPart += "<h2>{}</h2><table>".format( thisKey )
                            for line in errorDictionary['ByCategory'][category][thisKey]: # Line them up nicely in a table
                                if BibleOrgSysGlobals.debugFlag: assert( isinstance( line, str ) and line[-1]=="'" )
                                bits = line[:-1].split( " '", 1 ); assert( len(bits) == 2 ) # Remove the final quote and split at the first quote
                                if "Main Title 1" in bits[0]: bits[1] = "<b>" + bits[1] + "</b>"
                                categoryPart += "<tr><td>{}</td><td>{}</td></tr>".format( bits[0], bits[1] ) # Put in a table row
                            categoryPart += '</table>'
                        elif thisKey.endswith('Counts'): # it should be a list
                            print( "Counts key", thisKey )
                            categoryPart += "<h1>{}</h1>".format( thisKey )
                            if isinstance( errorDictionary['ByCategory'][category][thisKey], list ): # always true
                            #    for error in errorDictionary['ByCategory'][category][thisKey]:
                            #        if BibleOrgSysGlobals.debugFlag: assert( isinstance( error, str ) )
                            #        categoryPart += "<p>{}</p>".format( error )
                            #elif isinstance( errorDictionary['ByCategory'][category][thisKey], (dict, OrderedDict,) ):
                                for subCategory in errorDictionary['ByCategory'][category][thisKey]:
                                    #print( subCategory )
                                    if subCategory.endswith('Errors'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory )
                                        for error in errorDictionary['ByCategory'][category][BBB][subCategory]:
                                            categoryPart += "<p>{}</p>".format( error )
                                    elif subCategory.endswith('Counts'):
                                        categoryPart += "<h2>{}</h2>".format( subCategory ) + "<p>"
                                        for something in sorted(errorDictionary['ByCategory'][category][BBB][subCategory]):
                                            categoryPart += "{}:{} ".format( something, errorDictionary['ByCategory'][category][BBB][subCategory][something] )
                                        categoryPart += "</p>"
                                    else: print( "A weird 2" ); halt
                        else:
                            print( "Have left-over thisKey", thisKey )
                            continue # ignore for now temp ....................................................................
                            raise KeyError# it wasn't a list or a dictionary
                if categoryPart: # Create the error page for this catebory
                    webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle+" USFM Bible {} Checks".format(BBB) ) \
                                .replace( "__MAIN_PART__", categoryPart ).replace( "__EXTRAS__", '' ) \
                                .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                                #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
                    webPageFilename = "{}.html".format( category )
                    with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                        myFile.write( webPage )
                    categoryCommentDict = { 'Priority Errors': 'Errors that the program thinks are most important',
                                            'Load Errors': 'Errors discovered when loading the USFM files',
                                            'Fix Text Errors': 'Errors found in the actual text',
                                            'Versification Errors': 'Errors with the chapter and verse numbers',
                                            'USFMs': 'Errors to do with the Unified Standard Format Markers',
                                            'Validation Errors': 'Errors found on detailed checking of the USFMs',
                                            'Words': 'Possible spelling and other word errors and counts',
                                            'Characters': 'Possible punctuation and other character errors and counts',
                                            'Notes': 'Footnote and cross-reference errors and counts',
                                            'Headings': 'Titles, section headers and section cross-references',
                                            'Introduction': 'Errors in the introductory section',
                                            'Added Formatting': 'Placement of section headings and paragraph breaks, etc.',
                                            'Speech Marks': 'Possible errors to do with placement of quote marks',
                                        }
                    categoryIndexPart += '<tr><td><a href="{}">{}</a></td><td>{}</td></tr>'.format( webPageFilename, category, categoryCommentDict[category] if category in categoryCommentDict else '' )
            categoryIndexPart += '</table>'
        indexPart = ""
        help1Part = '<p>Note that the checking program does make some changes to some USFM markers internally, e.g., <b>\\s</b> will be converted internally to <b>\\s1</b>, and <b>\\q</b> to <b>\\q1</b>. ' + \
                        'You may need to be aware of this when comparing these messages with the actual codes present in your files.</p>'
        help2Part = '<p><b>Errors</b> entries give lists of possible errors and warnings. <b>Priority Errors</b> is our attempt for the program to pick out the more serious errors in your work—the same information is also available in the other lists of Errors.</p>' + \
                    '<p><b>Lines</b> entries list all lines in certain categories (such as titles or headings) so that you can visually check through the lists in order to see how consistent you have been throughout your work.</p>' + \
                    '<p><b>List</b> entries also list similar items for you to scan through. The <b>Modified Marker List</b> gives you a quick way to scan through all of the main USFM markers used in your file—if a marker occurs several times in a row, it only lists it once.</p>' + \
                    '<p><b>Counts</b> entries list counts of characters and words, etc. and are usually provided sorted in different ways. It’s often helpful to look at items that only occur one or two times in your work as they might indicate possible mistakes.</p>' + \
                    '<p>We are still working on improving error detection, removing false alarms, and better prioritising the errors and warnings. If you have any suggestions, use the <a href="__TOP_PATH__Contact.html">Contact Page</a> to let us know. Thanks.</p>'
        if BBBIndexPart: # Create the by book index page
            BBBIndexPart += '<small>{}</small>'.format( help1Part )
            webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle + " by Book" ) \
                        .replace( "__MAIN_PART__", BBBIndexPart ).replace( "__EXTRAS__", '' ) \
                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                        #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
            webPageFilename = "BBBIndex.html"
            with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                myFile.write( webPage )
            if len(givenBookList) == 1:
                #indexPart += '<p><a href="{}">All books</a></p>'.format( "All Books.html" )
                pass
            else:
                indexPart += '<p><a href="{}">All books</a></p>'.format( "All Books.html" )
                indexPart += '<p><a href="{}">By Bible book</a></p>'.format( webPageFilename )
        if categoryIndexPart: # Create the by category index page
            webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle + " by Category" ) \
                        .replace( "__MAIN_PART__", categoryIndexPart ).replace( "__EXTRAS__", '' ) \
                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                        #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
            webPageFilename = "categoryIndex.html"
            with open( os.path.join(pagesFolder, webPageFilename), 'wt' ) as myFile: # Automatically closes the file when done
                myFile.write( webPage )
            indexPart += '<p><a href="{}">By error category</a></p>'.format( webPageFilename )
        if indexPart:
            # Create the main index page
            if BBBIndexPart.count('<tr>') + categoryIndexPart.count('<tr>') < 10: # Let's just combine them (ignoring the two files already written above)
                indexPart = "<h1>By Bible book</h1>" + BBBIndexPart + "<h1>By error category</h1>" + categoryIndexPart
            indexPart += '<small>{}</small>'.format( help2Part )
            webPage = webPageTemplate.replace( "__TITLE__", ourTitle ).replace( "__HEADING__", ourTitle ) \
                        .replace( "__MAIN_PART__", indexPart ).replace( "__EXTRAS__", '' ) \
                        .replace( "__TOP_PATH__", defaultTopPath ).replace( "__SUB_PATH__", "/Software/" ).replace( "__SUB_SUB_PATH__", "/Software/BibleDropBox/" )
                        #.replace( "__TOP_PATH__", "../"*6 ).replace( "__SUB_PATH__", "../"*5 ).replace( "__SUB_SUB_PATH__", "../"*4 )
            webPageFilename = "index.html"
            webPagePath = os.path.join( pagesFolder, webPageFilename )
            if BibleOrgSysGlobals.verbosityLevel>3: print( "Writing error checks web index page at {}".format( webPagePath ) )
            with open( webPagePath, 'wt' ) as myFile: # Automatically closes the file when done
                myFile.write( webPage )
            #print( "Test web page at {}".format( webPageURL ) )

        return webPagePath if len(indexPart) > 0 else None
    # end of InternalBible.makeErrorHTML


    def getNumChapters( self, BBB ):
        """
        Returns the number of chapters (int) in the given book.
        Returns None if we don't have that book.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("getNumChapters( {} )").format( BBB ) )
        assert( len(BBB) == 3 )
        if not BibleOrgSysGlobals.BibleBooksCodes.isValidReferenceAbbreviation( BBB ): raise KeyError
        self.loadBookIfNecessary( BBB )
        if BBB in self:
            return self.books[BBB].getNumChapters()
        # else return None
    # end of InternalBible.getNumChapters


    def getNumVerses( self, BBB, C ):
        """
        Returns the number of verses (int) in the given book and chapter.
        Returns None if we don't have that book.
        """
        if BibleOrgSysGlobals.debugFlag and debuggingThisModule: print( t("getNumVerses( {}, {} )").format( BBB, repr(C) ) )
        assert( len(BBB) == 3 )
        if not BibleOrgSysGlobals.BibleBooksCodes.isValidReferenceAbbreviation( BBB ): raise KeyError
        self.loadBookIfNecessary( BBB )
        if BBB in self:
            if isinstance( C, int ): # Just double-check the parameter
                logging.debug( t("getNumVerses was passed an integer chapter instead of a string with {} {}").format( BBB, C ) )
                C = str( C )
            return self.books[BBB].getNumVerses( C )
    # end of InternalBible.getNumVerses


    def getContextVerseData( self, BCVReference ):
        """
        Search for a Bible reference
            and return a 2-tuple containing
                the Bible text (in a InternalBibleEntryList)
                along with the context.

        Expects a SimpleVerseKey for the parameter
            but also copes with a (B,C,V,S) tuple.

        Returns None if there is no information for this book.
        Raises a KeyError if there is no such CV reference.
        """
        #print( "InternalBible.getContextVerseData( {} )".format( ref ) )
        if isinstance( BCVReference, tuple ): BBB = BCVReference[0]
        else: BBB = BCVReference.getBBB() # Assume it's a SimpleVerseKeyObject
        #print( " ", BBB in self.books )
        self.loadBookIfNecessary( BBB )
        if BBB in self.books: return self.books[BBB].getContextVerseData( BCVReference )
        #else: print( "InternalBible {} doesn't have {}".format( self.name, BBB ) ); halt
    # end of InternalBible.getContextVerseData


    def getVerseData( self, BCVReference ):
        """
        Return (USFM-like) verseData (InternalBibleEntryList -- a specialised list).

        Returns None if there is no information for this book.
        Raises a KeyError if there is no CV reference.
        """
        #print( "InternalBible.getVerseData( {} )".format( BCVReference ) )
        result = self.getContextVerseData( BCVReference )
        #print( "  gVD", self.name, key, verseData )
        if result is None:
            if BibleOrgSysGlobals.debugFlag or BibleOrgSysGlobals.verbosityLevel>2: print( "InternalBible.getVerseData: no VD", self.name, key, result )
            #if BibleOrgSysGlobals.debugFlag: assert( BCVReference.getChapterNumberStr()=='0' or BCVReference.getVerseNumberStr()=='0' ) # Why did we get nothing???
        else:
            verseData, context = result
            if BibleOrgSysGlobals.debugFlag:
                assert( isinstance( verseData, InternalBibleEntryList ) )
                # The following numbers include end markers, i.e., \q1 xyz becomes q1,p~ xyz,¬q1
                if len(verseData)<1 or len(verseData)>30: print( "IB:vdLen", len(verseData), self.abbreviation, BCVReference )
                if len(verseData)>35: print( verseData )
                if self.abbreviation not in ('mhl','sua',): # This version has Matt 1:1-11 combined! 57 entries
                    assert( 1 <= len(verseData) <= 35 ) # Smallest is just a chapter number line
            return verseData
    # end of InternalBible.getVerseData


    def getVerseText( self, BCVReference, fullTextFlag=False ):
        """
        First miserable attempt at converting (USFM-like) verseData into a string.

        Uses uncommon Unicode symbols to represent various formatted styles

        Raises a KeyError if the key isn't found/valid.
        """
        result = self.getContextVerseData( BCVReference )
        if result is not None:
            verseData, context = result
            #print( "gVT", self.name, BCVReference, verseData )
            assert( isinstance( verseData, InternalBibleEntryList ) )
            #if BibleOrgSysGlobals.debugFlag: assert( 1 <= len(verseData) <= 5 )
            verseText, firstWord = '', False
            for entry in verseData:
                marker, cleanText = entry.getMarker(), entry.getOriginalText() if fullTextFlag else entry.getCleanText()
                if marker[0] == '¬': pass # Ignore end markers
                elif marker == 'c': pass # Ignore
                elif marker == 'c~': pass # Ignore text after chapter marker
                elif marker == 'c#': pass # Ignore print chapter number
                elif marker == 's1': verseText += '¥' + cleanText + '¥'
                elif marker == 'p': verseText += '¶' + cleanText
                elif marker == 'q1': verseText += '₁' + cleanText
                elif marker == 'q2': verseText += '₂' + cleanText
                elif marker == 'q3': verseText += '₃' + cleanText
                elif marker == 'q4': verseText += '₄' + cleanText
                elif marker == 'm': verseText += '§' + cleanText
                elif marker == 'v': firstWord = True # Ignore
                elif marker == 'v~': verseText += cleanText
                elif marker == 'p~': verseText += cleanText
                elif marker == 'vw':
                    if not firstWord: verseText += ' '
                    verseText += cleanText
                    firstWord = False
                else: logging.warning( "InternalBible.getVerseText Unknown marker {}={}".format( marker, repr(cleanText) ) )
            return verseText
    # end of InternalBible.getVerseText


    def writeBOSBCVFiles( self, outputFolderPath ):
        """
        Write the internal pseudoUSFM out directly with one file per verse.
        """
        BBBList = []
        for BBB,bookObject in self.books.items():
            BBBList.append( BBB )
            bookFolderPath = os.path.join( outputFolderPath, BBB + '/' )
            os.mkdir( bookFolderPath )
            bookObject.writeBOSBCVFiles( bookFolderPath )

        # Write the Bible metadata
        if BibleOrgSysGlobals.verbosityLevel > 2: print( "  " + _("Writing BCV metadata...") )
        metadataLines = 'BCVVersion = {}\n'.format( BCV_VERSION )
        if self.projectName: metadataLines += 'ProjectName = {}\n'.format( self.projectName )
        if self.name: metadataLines += 'Name = {}\n'.format( self.name )
        if self.abbreviation: metadataLines += 'Abbreviation = {}\n'.format( self.abbreviation )
        metadataLines += 'BookList = {}\n'.format( BBBList )
        with open( os.path.join( outputFolderPath, 'Metadata.txt' ), 'wt' ) as metadataFile:
            metadataFile.write( metadataLines )
    # end of InternalBible.writeBOSBCVFiles
# end of class InternalBible



def demo():
    """
    A very basic test/demo of the InternalBible class.
    """
    if BibleOrgSysGlobals.verbosityLevel > 0: print( ProgNameVersion )

    # Since this is only designed to be a base class, it can't actually do much at all
    IB = InternalBible()
    IB.objectNameString = "Dummy test Internal Bible object"
    if BibleOrgSysGlobals.verbosityLevel > 0: print( IB )
# end of demo


if __name__ == '__main__':
    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( ProgName, ProgVersion )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    demo()

    BibleOrgSysGlobals.closedown( ProgName, ProgVersion )
# end of InternalBible.py