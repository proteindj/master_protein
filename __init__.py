#!/usr/bin/env python
"""
PyMol plugin for MASTER protein search
connects to a remote server
author:   Tim Tregubov, 12/2014
"""

from pymol.wizard import Wizard
from pymol import cmd
from search_thread import *
from logo_thread import *
from logo_popup import *
#from Tkinter import *
import Tkinter as tk
from constants import *
#from tk_trial2 import *

URL = "http://ararat.cs.dartmouth.edu:5001/api/search"
LOGOURL = "http://ararat.cs.dartmouth.edu:5001/api/logo"

class MasterSearch(Wizard):
    """
    This class  will create the wizard for performing MASTER searches.
    """
    def __init__(self, app, _self=cmd):
        Wizard.__init__(self, _self)

        # Clean the slate
        self.cmd.unpick()
        self.app = app

        # Default values
        self.rmsd_cutoff = 1.0
        self.number_of_structures = 25
        self.full_match = False
        self.url = URL
        self.LOGOurl = LOGOURL

        self.ref = Wizard

        # default values for sequence logo UI
        self.operations = []
        self.searches = []
        self.database = DATABASE_TEST
        self.database_name = "Test"
        self.search = None # current search action
        self.operation = None # current operation

        self.dictionary = {}

        self.searchThread = None
        self.logoThread = None

        self.status = 'waiting for selection'
        self.searchProgress = 0.0
        self.errorMessage = ''
        self.makeLogo = 0
        
        self.popup_app = None
        self.done_adding = False
        self.live_app = False
        
        self.update()

    def update(self):
        """
        Checks to see what needs to be updated in/by the Wizard, updates, and quits.
        This could include opening a window to show the logo, updating the progress
        bar of an ongoing search, displaying an error or other message from a search...
        """

        if self.makeLogo == 3 and self.live_app != True:
            self.popup_app = WindowApp(self.app)
            self.live_app = True
        
        self.makeLogo = 0
        self.app.root.after(100, self.update)


    def set_searchProgress(self, progress):
        """
        Setter for search progress
        """
        self.searchProgress = progress
        self.cmd.refresh_wizard()

    def set_status(self, status):
        """
        Setter for status
        """
        self.status = status
        self.cmd.refresh_wizard()

    def set_errorMessage(self, mes):
        """
        Setter for error message
        """
        self.errorMessage = mes

    def cleanup(self):
        """
        Once we are done with the wizard, we should set various pymol
        parameters back to their original values.
        """
        self.stop_search()

    def logo_helper(self, flag):
        self.makeLogo = flag
    


    def get_panel(self):
        """
        sets up the main menu panel
        """
        rmsd_menu = self.create_rmsd_menu()
        self.menu['rmsd'] = rmsd_menu
        num_structures_menu = self.create_num_structures_menu()
        self.menu['num_structures'] = num_structures_menu
        full_matches_menu = self.create_full_matches_menu()
        self.menu['full_matches'] = full_matches_menu
        database_menu = self.create_database_menu()
        self.menu['database'] = database_menu

        '''
        sets up the menu ui for sequence logo
        '''
        select_search_menu = self.create_select_search_menu()
        self.menu['searches'] = select_search_menu

        # num is the type of display  1 is title only, 2 is button, 3 is dropdown
        return [[2, 'Search Menu','cmd.get_wizard().logo_helper(3)']]
    
    
    def set_rmsd(self, rmsd):
        """
        This is the method that will be called once the user has
        selected an rmsd cutoff via the wizard menu.
        """
        self.rmsd_cutoff = rmsd
        self.cmd.refresh_wizard()


    def set_database(self, database):
        """
        This is the method that will be called once the user has
        selected an database via the wizard menu.
        """
        if(database == "Full"):
            self.database = DATABASE_FULL
            self.database_name = "Full"
        elif(database == "Test"):
            self.database = DATABASE_TEST
            self.database_name = "Test"
        self.cmd.refresh_wizard()


    def create_rmsd_menu(self):
        """
        This method will create a wizard menu for the possible RMSD cutoff values.
        Currently the values range from 0.1 to 2 A RMSD.
        """
        rmsd_menu = [[2, 'RMSD Cutoff', '']]
        for rmsd_choice in range(1,21):
            rmsd = float(rmsd_choice) / 10.0
            rmsd_menu.append(
                [1, str(rmsd), 'cmd.get_wizard().set_rmsd(' + str(rmsd) + ')'])
        return rmsd_menu


    def set_num_structures(self, num_structures):
        """
        This is the method that will be called once the user
        has set the maximum number of structures to return.
        """
        self.number_of_structures = num_structures
        self.cmd.refresh_wizard()


    def create_num_structures_menu(self):
        """
        This method will create a wizard menu for the possible number of structures
        to return.  Values range from 10 to 2000.
        """
        num_structures_menu = [[2, 'Number of Results', '']]
        for n in [10, 20, 50, 100, 200, 500]:
            num_structures_menu.append(
                [1, str(n), 'cmd.get_wizard().set_num_structures(' + str(n) + ')'])
        return num_structures_menu


    def create_database_menu(self):
        """
        This method will create a wizard menu for the database to run the search with
        """
        database_menu = [[2, 'Database', '']]
        database_menu.append([1, "Full Database", 'cmd.get_wizard().set_database("Full")'])
        database_menu.append([1, "Test Database", 'cmd.get_wizard().set_database("Test")'])

        return database_menu


    def set_full_matches(self, full_matches):
        """
        """
        self.full_match = full_matches
        self.cmd.refresh_wizard()


    def create_full_matches_menu(self):
        """
        creates the wiard menu for the full matches boolean option
        """
        full_matches_menu = []
        full_matches_menu.append([2, 'Full Matches', ''])
        full_matches_menu.append(
            [1, 'No', 'cmd.get_wizard().set_full_matches(False)'])
        full_matches_menu.append(
            [1, 'Yes', 'cmd.get_wizard().set_full_matches(True)'])
        return full_matches_menu


    def add_new_search(self, search_id):
        '''
        add current search to search history after it finishes
        '''
        # print 'add new search'
        self.searches.append(search_id)
        self.cmd.refresh_wizard()

        # Trip flag for window
        self.done_adding = True
    


    def create_select_search_menu(self):

        select_search_menu = []
        select_search_menu.append([2, 'History', ''])
        for i in range(len(self.searches)):
            select_search_menu.append([1, 'id: '+self.searches[i], 'cmd.get_wizard().set_search('+str(i)+')'])

        return select_search_menu


    def set_search(self, i):
        
        self.search = self.searches[int(i)]
        print self.search
        self.cmd.refresh_wizard()


    def launch_logo_search(self, flag):
        """
        launches the show logo operation in the separate thread
        does some basic checking and gets selection
        """

        if self.search is None:
            print 'please select target search'
            return
        
        else:
            
            self.status = 'logo request launched'
            self.cmd.refresh_wizard()

            self.logoThread = LogoThread(
                self.rmsd_cutoff,
                self.dictionary[self.search],
                int(flag),
                self.LOGOurl,
                self.cmd)
            self.logoThread.start()
            self.logoThread.join()
           
            self.status = 'logo request finished'
            self.cmd.refresh_wizard()
            path = SEARCH_CACHE + str(self.search)
            with open(path, 'r') as f:
                residues = f.readline().strip()

            query = self.dictionary[self.search]
            self.makeLogo = 0
            
            self.popup_app.display_menu_logo(self.app, query, residues, self.rmsd_cutoff, self.LOGOurl, flag, self)


    def stop_logo(self, message=''):
        if self.logoThread:
            self.logoThread.stop(message)

    def launch_search(self):
        """
        launches the search in the separate thread
        does some basic checking and gets selection
        """
        
        # gets the active selections from pymol
        active_selections = cmd.get_names('selections', 1)
        if len(active_selections) == 0:
            self.status = 'no selection'
        else:

            selection = active_selections[0]
            print "The active selections are " + str(selection)
            pdbstr = cmd.get_pdbstr(selection)
            print 'pdbstr is', pdbstr
            self.stop_search()
            self.searchThread = SearchThread(self,
                self.rmsd_cutoff,
                self.number_of_structures,
                self.full_match,
                self.database,
                pdbstr,
                self.url,
                self.cmd,
                self.dictionary)
            self.searchThread.start()
            self.status = 'search launched'
            self.searchProgress = 0
        self.cmd.refresh_wizard()

    def stop_search(self, message=''):
        if self.searchThread:
            self.searchThread.stop(message)
    

    def get_prompt(self):
        self.prompt = None
        if (self.status == 'waiting for selection'):
             self.prompt = [ 'Make a selection and then hit search...' ]
        elif (self.status == 'logo request launched'):
            self.prompt = [ 'Launched logo generation' ]
        elif (self.status == 'logo request finished'):
            self.prompt = [ 'Received logo from server' ]
            self.status = [ 'waiting for selection' ]
        elif (self.status == 'search launched'):
            self.prompt = [ 'Searching (%d%%)...' % round(100*self.searchProgress)  ]
        elif (self.status == 'search complete'):
            self.prompt = [ 'Search complete...' ]
            self.status = 'waiting for selection'
        elif (self.status == 'no selection'):
            self.prompt = [ 'Error: must have an active selection!' ]
            self.status = 'waiting for selection'
        return self.prompt

'''
Wrapper class for the MasterSearch client application
'''
def master_search(app):
    """
    MASTER search
    """

    # create a folder for storing temporary data
    if not os.path.exists(MAIN_CACHE):
        os.makedirs(MAIN_CACHE)

    if not os.path.exists(SEARCH_CACHE):
        os.makedirs(SEARCH_CACHE)

    if not os.path.exists(LOGO_CACHE):
        os.makedirs(LOGO_CACHE)

    wiz = MasterSearch(app)
    cmd.set_wizard(wiz)


# add "master_search" as pymol command
cmd.extend('master_search', master_search)

# trick to get "wizard master_search" working
sys.modules['pymol.wizard.master_search'] = sys.modules[__name__]

try:
    from pymol.plugins import addmenuitem

    # add item to plugin menu
    def __init_plugin__(self):
        addmenuitem('MASTER Search v0.1', lambda s = self: master_search(s))
except:
    def __init__(self):
        self.menuBar.addmenuitem('Plugin', 'command', 'MASTER search',
                                 label='MASTER search', command= lambda s = self: master_search(s))

