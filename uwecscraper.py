#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 17 17:18:04 2020

@author: amethyst
"""

#%%

import pandas as pd
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import hashlib
import os
from os import listdir
from os.path import isfile, join, isdir

#%%

URL = 'https://www.uwec.edu/coronavirus-updates/dashboard/'
default_data_location = "/Users/amethyst/Dropbox/work/covid/data/daily_website_saves/"

#%%

def read_daily_websites(path = default_data_location):
    """
    reads soup (but not images)
    into memory
    for all saved soups.
    """
    
    from os import listdir
    from os.path import isfile, join
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f)) and f!='.DS_Store']
    
    data = {}
    for f in onlyfiles:
        with open(join(path, f),'r',encoding='utf-8') as fin:
            try:
                data[f] = BeautifulSoup(fin.read(), 'html.parser')
            except Exception:
                print('failed to read {}'.format(f))
                raise
        
    return data


#%% Save and load

def download_img_and_save(url, path):
    """
    downloads image to disk, canonicalizing the pathname if suitably named.
    
    probably fragile if name pattern changes.
    """
    import requests
    a = url.find("UW-EauClaireCOVID-19DataTrackerDashboard")
    b = len(url)
    fn = url[a:b].replace('/','_')
    fn = '{}/{}'.format(path,fn)
    with open(fn, "wb") as f:
        f.write(requests.get(url).content)
            
            
def is_new_data(soup):
    """
    a wrapper function, checking whether data is new based on all saved criteria
    """
    
    return is_new_based_on_html(soup) or is_new_based_on_imgs(soup)
    
def is_new_based_on_imgs(soup):
    """
    checks whether the soup is new, based on whether we already have a copy of
    the tableau images.
    
    this was made necessary on sept 25, 2020.
    
    downloads all images from soup, hashes them.  hashes old images.  
    sees if there's a new image we didn't already have.
    deletes temp images.
    
    there's an improvement, in that the new images are already downloaded, so if you go on to save the page and its images, the re-download is a waste.  oh well.
    """

    
    
    prev_hashes = get_prev_img_hashes()
    temp_hashes = get_temp_img_hashes(soup)

    if len(temp_hashes.difference(prev_hashes))>0:
        return True
    
    return False

def get_prev_img_hashes(path = default_data_location):
    """
    computes the hash of all saved images in all image folders in `path`
    returns a `set` of the hashes.
    """
    img_folders = get_all_image_folders(path)
    
    hashes = set()
    
    
    for f in img_folders:
        arst = join(default_data_location,f)
        onlypngs = [join(arst,img) for img in listdir(arst) if isfile(join(arst, img)) and img.find('.png')>=0]
        for p in onlypngs:
            with open(p,'rb') as fin:
                q = fin.read()
                
                hashes.add(get_hash(q))
                
    return hashes
    
def get_temp_img_hashes(soup, delete_when_done = True):
    """
    computes the hash of all new images.  returns a `set` of them.
    
    works by making a tempdir, and downloading the images to it.
    computes the hashes
    deletes the tempdir
    """
    tempdir = join(default_data_location,"tempimgs")
    if not os.path.exists(tempdir):
        os.mkdir(tempdir)
    save_all_tableau_images(soup, tempdir)
    temp_hashes = set()
    
    onlypngs = [f for f in listdir(tempdir) if isfile(join(tempdir, f)) and f.find('.png')>=0]
    for img in onlypngs:
        with open(join(tempdir,img),'rb') as fin:
            q = fin.read()
            temp_hashes.add(get_hash(q))
            
    if delete_when_done:
        import shutil
        shutil.rmtree(tempdir)
    
    return temp_hashes
    
    

def get_all_image_folders(path):
    
    return [f for f in listdir(path) if isdir(join(path, f)) and f.find("imgs")>=0]

def is_new_based_on_html(soup):
    """
    determines whether the soup is new, based on hashing with stored soups.  
    
    this should probably also be used in conjunction with other saved data, incase any piece of it changes between crawls.
    """
    m = hashlib.sha256()
    m.update(str(soup).encode('utf-8'))
    curr_hash = m.digest()
    
    data = read_daily_websites()
    for k,v in data.items():
        then_hash = get_hash(str(v))
        if curr_hash == then_hash:
            return False
        
    return True

def get_hash(thing):
    """
    a helper object for producing sha256 hashes from anything.
    
    if it can't tolerate the type of object you pass, will raise an exception.  it's probably the wrong type of exception to be raising.
    """
    n = hashlib.sha256()
    
    if isinstance(thing,str):
        n.update(thing.encode('utf-8' ))
    elif isinstance(thing, bytes):
        n.update(thing)
    else:
        raise RuntimeError("unknown type: {}".format(str(type(thing))))
            
    return(n.digest())
    
def gen_filename_from_date(path,date,autoincrement = True):
    """
    makes a datetime object into a valid filename, using the iso format
    """
    
    fname = date.isoformat().replace(':','.')
    
    if autoincrement:

        onlyfiles = [f for f in listdir(path) if isfile(join(path, f)) and f!='.DS_Store']
        
        highest = -1
        for f in onlyfiles:
            temp_f = f.strip('.html')
            if fname == temp_f[0:19]:
                if int(temp_f.split('_')[1]) > highest:
                    highest = int(temp_f[20:])
                
    
    fname = "{}/{}_{}.html".format(path,fname,highest+1)
    return fname


def save_all_tableau_images(soup, path):
    """
    saves all images from soup, that have the word "tableau" in the url, to the specified path.
    """
    
    imgs = soup.find_all('img')
    for im in imgs:
        s = im['src']
        if s.find('tableau')>=0:
            download_img_and_save(s,path)
    
    params = soup.find_all('param')
    for p in params:
        n = p['name']
        if n.find('static_image')==0:
            if p['value'].find('tableau'):
                download_img_and_save(p['value'],path)
                
    
def save_html(soup, date, path=default_data_location):
    """
    required arg: soup -- a result from the .content attribute of getting a page with BS.
    
    optional arg: date as a datetime object.  
    if not supplied, will use the current time.
    """
    import os
    if type(date)!=datetime:
        raise TypeError("date must be a `datetime` object")
            
    
    fname = gen_filename_from_date(path,date)
    
    
    p = fname[:-5]+'imgs'
    os.mkdir(p)
    save_all_tableau_images(soup, p)
    
    with open(fname,'w', encoding='utf-8') as fout:
        fout.write(str(soup))
        
    print("saved soup to file `{}`".format(fname))
    return fname

def gather_current(url=URL):
    """
    gets the soup for the page, as it is currently on yon internet
    """
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup

    
def gather_and_save(url=URL,even_if_old = False):
    """
    gets the current soup, as on the internet. 
    checks if we already have it.  
    - if do, no save.  
    - if not, autosave using date, defaulting to now in case can't read date from page (sept 25 mod to source made this necessary.)
    
    there is an option to save even if we already have it.  this is guaranteed to not overwrite old data, because every data has an incremented counter in its name.  huzzah.
    """
    
    soup = gather_current(url=url)
    
    try:
        date = get_date(soup)
    except RuntimeError as e:
        now = datetime.now()
        date = datetime(now.year,now.month,now.day,now.hour,now.minute,now.second)
        print('unable to read date from source :(   using datestring {}'.format(date))
        
    if even_if_old or is_new_data(soup):
        save_html(soup, date)
    else:
        print('already had the data from {}'.format(date))
    return soup




#%% Date functions
    
def UWEC_date_to_datetime_til_sept14_2(datestring):
    hh,mm = list(map(int,datestring.split()[0].split(':')))
    ampm = datestring.split()[1].split('.')

    MM,dd,yy = list(map(int,datestring.split()[2].split('/')))
    
    return datetime(2000+yy,MM,dd,hh+int(ampm[0]=='p')*12,mm)

def get_date_til_sept14_2(soup):
    h4 = soup.find_all('h4')
    for h in h4:
        t = str(h.findAll(text=True))
        s = re.search('([0-9]+:[0-9]+ [a,p].m. [0-9]+/[0-9]+/[0-9]+)',t)
        if s!=None:
            q = s.span()
            d = UWEC_date_to_datetime_til_sept14_2(t[q[0]:q[1]])
            return d
        
    raise RuntimeError('unable to find MM/DD/YY format')
    
    

def abbr_to_month(abbr):
    abbr_map = {'Sept.': 9,'Oct.': 10,'Nov.':11, 'Dec.':12}
    return abbr_map[abbr]


# up to but not including 9/25
def UWEC_date_to_datetime_til_sept25(datestring):

    hh,mm = list(map(int,datestring.split()[0].split(':')))
    ampm = datestring.split()[1].split('.')

    MM = abbr_to_month(datestring.split()[2])
    dd = int(datestring.split()[3])
    yy = 20
    
    return datetime(2000+yy,MM,dd,hh+int(ampm[0]=='p')*12,mm)



# up to but not including 9/25
def get_date_til_sept25(soup):
    import unicodedata
    h4 = soup.find_all('h4')
    for h in h4:
        t = str(h.find(text=True))
        t = unicodedata.normalize("NFKD", t)
        t.replace('\xa0',' ')
        s = re.search('([0-9]+:[0-9]+ [a,p].m. [A-z]+. [0-9]+)',t)
        if s!=None:
            q = s.span()
            d = UWEC_date_to_datetime_til_sept25(t[q[0]:q[1]])
            return d
        
    raise RuntimeError('unable to find Mo. DD format')
    
    
# a stupid wrapper function because of varying date formats.
def get_date(soup):
    try:
        return get_date_til_sept14_2(soup)
    except RuntimeError as e1:
        try:
            return get_date_til_sept25(soup)
        except RuntimeError:
            raise e1
    
    

#%% Sept 14late - 

def get_col_labels_sept14_(data_cells):
    
    return col_labels

#%%  sept 14
        
def get_col_labels_early_sept14(data_cells):
    col_labels = []
    offset = 13
    for ii in range(5):
        col_labels.append(str(data_cells[ii+offset].findAll(text=True)[0]))
    return col_labels

def process_rectangular_data_early_sept14(soup):
    from collections import defaultdict
    
    data_cells = soup.find_all('td')
    
    col_labels = get_col_labels_early_sept14(data_cells)
    
    data_by_col = defaultdict(list)
    data_by_col["row_labels"] = []
    
    for ii in [0,1,3,4,5]:
        data_by_col["row_labels"].append(str(data_cells[ii*6].findAll(text=True)[0]))
        for jj in range(4):
            data_by_col[col_labels[jj]].append(int(str(data_cells[ii*6+jj+1].findAll(text=True)[0])))
        jj=4
        data_by_col[col_labels[jj]].append(float(str(data_cells[ii*6+jj+1].findAll(text=True)[0]).strip('%')))
    
    rect_data = pd.DataFrame(data_by_col)
    
    return  rect_data

def process_vect_data_early_sept14(soup):
    vect_data = []
    
    return vect_data

def process_data_early_sept14(soup):
    
    return process_rectangular_data_early_sept14(soup), process_vect_data_early_sept14(soup)
#%% sept 10
    
def process_data_sept10(soup):
    data_cells = soup.find_all('td')
    print(data_cells)
    
    what = ["Positive cases", "Total # PCR Tests", "Total # of Antigen tests"]
    
    todays_data = data_cells[5:8]
    today = [None]*3
    for ii in range(3):
        today[ii] = int(re.search('([0-9]+)',str(todays_data[ii].findAll(text=True))).group(0))

    this_weeks_data = data_cells[9:12]
    thisweek = [None]*3
    for ii in range(3):
        thisweek[ii] = int(re.search('([0-9]+)',str(this_weeks_data[ii].findAll(text=True))).group(0))

    UWEC = pd.DataFrame({"What": what, "This week": thisweek, "Today": today})
    
    
    s = 15
    ricelake_data = data_cells[s:s+1]
    ricelake = int(re.search('([0-9]+)',str(ricelake_data[0].findAll(text=True))).group(0))
    ricelake

    s = 17
    marshfield_data = data_cells[s:s+1]
    marshfield = int(re.search('([0-9]+)',str(marshfield_data[0].findAll(text=True))).group(0))
    marshfield
    
    s = 19
    students_in_quarantine_data = data_cells[s:s+1]
    students_in_quarantine = int(re.search('([0-9]+)',str(students_in_quarantine_data[0].findAll(text=True))).group(0))
    students_in_quarantine
    
    s = 21
    students_in_isolation_data = data_cells[s:s+1]
    students_in_isolation = int(re.search('([0-9]+)',str(students_in_isolation_data[0].findAll(text=True))).group(0))
    students_in_isolation
    
    s = 23
    students_hospitalized_data = data_cells[s:s+1]
    students_hospitalized = int(re.search('([0-9]+)',str(students_hospitalized_data[0].findAll(text=True))).group(0))

    
    OtherData = pd.DataFrame({"Rice Lake": [ricelake], "Marshfield": [marshfield], "Students in quarantine": [students_in_quarantine], "Students in isolation": [students_in_isolation], "Students Hospitalized": [students_hospitalized]})

    return UWEC, OtherData

#%%
    
    

    
    
    