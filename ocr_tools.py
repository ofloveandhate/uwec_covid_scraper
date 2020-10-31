import pytesseract as pt
from PIL import Image
from PIL.ImageOps import grayscale as gs

# Set up cropping boxes.
# Found by opening in GIMP, looking at corner coordinates
daily_numbers_box = (10, 127, 795, 245)

# image_path is the location of today's numbers image.
# This is likely
#   "<uwec_covid_scraper_root>/downloads/2020-10-03T13.24.17_0imgs/UW-EauClaireCOVID-19DataTrackerDashboardHSTiles_HealthServicesTiles_1.png"
def daily_numbers(im, report = False, from_file = False):
    # Load the saved image, 
    #   crop to the numbers, 
    #   convert to greyscale,
    #   extract to string,
    # Then trim the string 
    if from_file:
        im = Image.open(im)
        
    numbers = im.crop(daily_numbers_box)
    num_gs = gs(numbers)
    text = pt.image_to_string(num_gs)

    # Trim "%", newlines, etc from end
    # - Then remove commas from numbers
    # - Then 
    cstext = text[:text.index("%")]
    cstext = cstext.replace(",", "") # remove commas from numbers (e.g. 1,234 ~~> 1234)
    vals = cstext.split(" ")
    vals[0] = int(vals[0])
    vals[1] = int(vals[1])
    vals[2] = float(vals[2])
    if report:
        print("Daily numbers:")
        print("Positive tests: {}\nTotal tests: {}\n Percent positive: {}\n".format(vals[0], vals[1], vals[2]))

    return vals

# data should be a list-like containing (new cases, new tests, percentage)
# percentage is actually re-calculated here
def add_new_data(data, tableCSV):
    import pandas as pd
    from datetime import date

    # Read in stored table of covid data
    # Columns: date, daily_pos, daily_tests, daily_pcnt, cumul_pos, cumul_test
    covidDF = pd.read_csv(tableCSV)
    # Date stored as "YYYY-mm-dd" aka isoformat
    today = date.today().isoformat()

    # Convert to int; we will re-calculate percentage
    data = [int(d) for d in data]
    percent = round(100*data[0]/data[1], 1)

    cumul_pos = covidDF.cumul_pos.iloc[-1] + data[0]
    cumul_test = covidDF.cumul_test.iloc[-1] + data[1]

    # Easy to append row from dictionary. 
    # Complains unless values are lists
    new_data = {
        "date": [today],
        "daily_pos": [data[0]],
        "daily_tests": [data[1]],
        "daily_pcnt": [percent],
        "cumul_pos": [cumul_pos],
        "cumul_test": [cumul_test]
        }

    covidDF = covidDF.append(pd.DataFrame(new_data), ignore_index = True)

    covidDF.to_csv(tableCSV, index=False)
