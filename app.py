from flask import Flask, render_template, flash, redirect, url_for
from config import Config
from forms import SubmitForm

from dotenv import load_dotenv
load_dotenv()
import os
import re

import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.cluster.util import cosine_distance
import numpy as np
import networkx as nx
import random

api_key = os.getenv("api_key")


app = Flask(__name__)
app.config.from_object(Config)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about/')
def about():
    return render_template("about.html")

@app.route('/contact/')
def contact():
    return render_template("contact.html")

@app.route('/presentation/')
def presentation():
    return render_template("presentation.html")

@app.route('/content/', methods=['GET', 'POST'])
def content():
    form = SubmitForm()
    if form.validate_on_submit():
        zipCode = form.zipCode.data
        return redirect(url_for('contentresult', zipCode=zipCode))
    return render_template('content.html', form=form)

@app.route('/contentresult/<zipCode>')
def contentresult(zipCode):
    import json
    import requests
    import math
    import pandas as pd
    import numpy as np

    from bokeh.models import ColumnDataSource, LinearColorMapper
    from bokeh.plotting import figure
    from bokeh.resources import CDN
    from bokeh.embed import components
    from bokeh.transform import transform


    '''======================================================
    SECTION: GET ZIP, RELEVANT FACILITIES, AND REC AREA NAMES
    ======================================================'''

    #get zip data
    zips = pd.read_csv('./data/zipsandfacilities.csv')
    zips['Zip'] = zips['Zip'].astype('str')

    #get the facility ids
    relevantFacilities = zips[zips['Zip'] == zipCode]['relevantFacilities'].tolist()
    if len(relevantFacilities) == 0:
        recNames = ["No campsites in that area"]
    else:
        relevantFacilities = relevantFacilities[0]
        relevantFacilities = relevantFacilities[1:-1]
        relevantFacilities = relevantFacilities.split(", ")

        #get facil data
        facilities = pd.read_csv('./data/facidnamedesc.csv')
        facilities['facilityid'] = facilities['facilityid'].astype('str')

        #if some, get their names
        recNames = [facilities[facilities['facilityid'] == x]['RecAreaName'].values[0] for x in relevantFacilities]
        recNames = list(set(recNames))

    '''=====================================
    SECTION: CHART OF AVAILABLE ACTIVITIES
    ====================================='''
    test = relevantFacilities
    popularactivities = ['DAY USE AREA', 'BOATING', 'WINTER SPORTS', 'EVENING PROGRAMS', 'HUNTING',
                         'HISTORIC & CULTURAL SITE',
                         'EDUCATIONAL PROGRAMS', 'RANGER STATION', 'OFF ROAD VEHICLE TRAILS', 'HISTORIC SITES',
                         'CAVING',
                         'WATER SKIING', 'DISC GOLF', 'ACCESSIBLE SWIMMING', 'KAYAKING', 'SWIMMING', 'SWIMMING SITE',
                         'BEACHCOMBING', 'VISITOR CENTER', 'SURFING', 'ENVIRONMENTAL EDUCATION'
                         ]

    facilact = pd.read_csv('./data/facilactivlist.csv')
    facilact['facilityid'] = facilact['facilityid'].astype('str')
    '''['facilityid' 'activlist']'''

    facilactsub = facilact.loc[facilact['facilityid'].isin(test)]

    # these will be my columns, remove uniformative ones
    relevantactivities = []
    for x in facilactsub['activlist'].values.tolist():
        for y in x[1:-1].split(','):
            y = y.replace("'", "").strip()
            relevantactivities.append(y)
    relevantactivities = set(relevantactivities)
    exclude = ['CAMPING']
    relevantactivities = [x for x in relevantactivities if x not in exclude]

    #a little processing for nongraphical results
    popularavailable = [x for x in relevantactivities if x in popularactivities]
    popularavailablestr = ', '.join(popularavailable).title()

    basicavailable = [x for x in relevantactivities if x not in popularavailable]
    basicavailablestr = ', '.join(basicavailable).title()

    # first will setup basic df with relevant facilities
    heatdf = pd.DataFrame(np.array(test), columns=['facilityid'])

    # now want to add columns via relevant activities and an array of the values
    for col in relevantactivities:
        values = []
        for facil in test:
            if col in facilactsub[facilactsub['facilityid'] == facil]['activlist'].values[0]:
                if col in popularactivities:
                    values.append(2)
                else:
                    values.append(1)
            else:
                values.append(0)
        heatdf[col] = values

    #change from facilityid to rec area and drop any duplicates that emerge
    for index, row in heatdf.iterrows():
        facil = row['facilityid']
        recarea = facilities[facilities['facilityid'] == facil]['RecAreaName'].values[0]
        heatdf.iloc[index,0] = recarea
    heatdf = heatdf.drop_duplicates(subset=['facilityid'])


    # now the bokeh heat map
    heatdf = heatdf.set_index("facilityid")
    heatdf.columns.name = 'activities'
    heatdfstack = pd.DataFrame(heatdf.stack(), columns=['value']).reset_index()
    source = ColumnDataSource(heatdfstack)

    colors = ["#FFFFFF", "#D2D7CE", "#3f5335"]
    mapper = LinearColorMapper(palette=colors, low=0, high=2)

    pp = figure(sizing_mode="stretch_width", plot_height=500, title="Available and Popular Activities",
               y_range=list(heatdf.index), x_range=list(reversed(heatdf.columns)),
               toolbar_location=None, tools="", x_axis_location="above")

    pp.rect(y="facilityid", x="activities", width=1, height=1, source=source,
           line_color='grey', fill_color=transform('value', mapper))

    pp.xaxis.major_label_orientation = math.pi / 4


    # unpack bokeh figure
    script2, div2 = components(pp)

    '''=====================================
       SECTION: CHART OF AVAILABLE ATTRIBUTES
       ====================================='''
    relevantParent = [facilities[facilities['facilityid'] == facil]['ParentRecAreaID'].values[0] for facil in relevantFacilities]
    relevantParent = [str(x) for x in relevantParent]
    popularattributes = ['Food Locker_Y','Shade_Yes','Shade_Full','Tent Pad_Y','Ice_Y','Site Access_Drive-In','Electricity Hookup_30 amp',
                         'Equipment Mandatory_0','Drinking Water_Y','Driveway Surface_Gravel','Driveway Surface_Paved','Proximity to Water_Riverfront',
                         'Proximity to Water_Oceanfront','Condition Rating_Prime','Location Rating_Prime','Checkin Time_early']

    facilattr = pd.read_csv('./data/facilattriblistvalues.csv')
    facilattr['facilityid'] = facilattr['facilityid'].astype('str')
    '''[facilityid,attriblist]'''

    facilattrsub = facilattr.loc[facilattr['facilityid'].isin(relevantParent)]

    # these will be my columns, remove uniformative ones
    relevantattributes = []
    for x in facilattrsub['attriblist'].values.tolist():
        for y in x[1:-1].split(','):
            y = y.replace("'", "").strip()
            relevantattributes.append(y)
    relevantattributes = set(relevantattributes)

    # a little processing for nongraphical results
    Apopularavailable = [x for x in relevantattributes if x in popularattributes]
    Apopularavailablestr = ', '.join(Apopularavailable).title()

    popularnotavailable = [x for x in popularattributes if x not in relevantattributes]
    popularnotavailablestr = ', '.join(popularnotavailable).title()

    otheravailable = [x for x in relevantattributes if x not in popularattributes]
    otheravailablestr = ', '.join(otheravailable).title()



    '''=====================================
    SECTION: CHART OF TYPICAL ANNUAL TRAFFIC
    ====================================='''
    reservationsAll = pd.read_csv('./data/CountsReservandPeople.csv',na_values='-')
    '''reminder of columns
    ['facilityid', 'total2019count', 'Jan19', 'Feb19', 'Mar19', 'Apr19',
           'May19', 'Jun19', 'Jul19', 'Aug19', 'Sep19', 'Oct19', 'Nov19', 'Dec19',
           'total2019people', 'Jan19people', 'Feb19people', 'Mar19people',
           'Apr19people', 'May19people', 'Jun19people', 'Jul19people',
           'Aug19people', 'Sep19people', 'Oct19people', 'Nov19people',
           'Dec19people']'''

    reservationsAll.fillna(0, inplace=True)
    reservationsAll['facilityid'] = reservationsAll['facilityid'].astype('str')

    reservations = reservationsAll[reservationsAll['facilityid'].isin(relevantFacilities)]
    reservations = reservations.rename(columns={"Jan19people": "Jan",
                                                "Feb19people": "Feb",
                                                "Mar19people": "Mar",
                                                "Apr19people": "Apr",
                                                "May19people": "May",
                                                "Jun19people": "Jun",
                                                "Jul19people": "Jul",
                                                "Aug19people": "Aug",
                                                "Sep19people": "Sep",
                                                "Oct19people": "Oct",
                                                "Nov19people": "Nov",
                                                "Dec19people": "Dec",
                                                })
    reservationsMeans = reservations.iloc[:, 15:].mean()

    resMeansdf = reservationsMeans.to_frame(name='people')
    resMeansdf.reset_index(inplace=True)
    resMeansdf = resMeansdf.rename(columns={"index": "month"})

    # setup figure for bokeh
    p = figure(title="Monthly Traffic", x_range=resMeansdf.month, x_axis_label='Month', y_axis_label='Number of People', plot_height=350,
               plot_width=800)
    p.vbar(x=resMeansdf.month, top=resMeansdf.people, legend_label=zipCode, fill_color="#3f5335", line_color='black')  # source=source,

    #unpack bokeh figure
    script1, div1 = components(p)
    cdn_js = CDN.js_files[0]
    cdn_widg = CDN.js_files[1]
    cdn_css = CDN.css_files


    '''=====================================
       SECTION: Campsite Summaries
       ====================================='''
    facilities = pd.read_csv('./data/facidnamedesc.csv')
    facilities['facilityid'] = facilities['facilityid'].astype('str')
    facilities['ParentRecAreaID'] = facilities['ParentRecAreaID'].astype('str')
    facilities['RecAreaDescription'] = facilities['RecAreaDescription'].astype('str')

    faciltextsub = [facilities[facilities['ParentRecAreaID'] == x]['RecAreaDescription'].values[0] for x in relevantParent]
    faciltextraw = ' '.join(faciltextsub)

    #clean up html tags
    faciltext = re.sub(re.compile('<.*?>'), '', faciltextraw)
    faciltextlist = faciltext.replace(',','.').split('.')
    faciltextlist = [x.split(' ') for x in faciltextlist]
    faciltextlist = [x for x in faciltextlist if len(x)>=5]

    def simscore(clause1, clause2, stopwords=None):
        if stopwords is None:
            stopwords = []

        clause1 = [x.lower() for x in clause1]
        clause2 = [x.lower() for x in clause2]

        coll = list(set(clause1 + clause2))

        v1 = [0] * len(coll)
        v2 = [0] * len(coll)

        for word in clause1:
            if word in stopwords:
                continue
            v1[coll.index(word)] += 1

        for word in clause2:
            if word in stopwords:
                continue
            v2[coll.index(word)] += 1

        return 1 - cosine_distance(v1, v2)

    def simmatrix(clauses, stop_words):
        matrix = np.zeros((len(clauses), len(clauses)))

        for idx1 in range(len(clauses)):
            for idx2 in range(len(clauses)):
                if idx1 == idx2:
                    continue
                matrix[idx1][idx2] = simscore(clauses[idx1], clauses[idx2], stop_words)

        return matrix

    def summary(raw, top_n=5):
        stop_words = stopwords.words('english')
        result = []

        matrixAll = simmatrix(raw, stop_words)

        graph = nx.from_numpy_array(matrixAll)
        scores = nx.pagerank_numpy(graph)

        ranked = sorted(((scores[i], s) for i, s in enumerate(raw)), reverse=True)

        for i in range(top_n):
            result.append(" ".join(ranked[i][1]))

        return ';\n '.join(result)

    finalsummary = ''

    if len(relevantParent) > 0:
        # incorporate above activities
        subact = random.sample(popularavailable, 3)
        finalsummary += "A great location to enjoy " + ", ".join(subact) + ", and " + random.choice(subact) + ".  "
        # incorporate above attributes
        subatt = random.sample(Apopularavailable, 3)
        finalsummary += "Here, you can kick back and take advantage of " + ", ".join(subatt) + ", and " + random.choice(subatt) + ".  "
        finalsummary += summary(faciltextlist, 10)




    return render_template("contentresult.html", zipCode=zipCode, recNames=recNames,
                           basicavailablestr=basicavailablestr, popularavailablestr=popularavailablestr,
                           popularnotavailable=popularnotavailable,Apopularavailablestr=Apopularavailablestr,
                           otheravailablestr=otheravailablestr, finalsummary = finalsummary,
                           script1=script1, div1=div1,
                           script2=script2, div2=div2,
                           cdn_js=cdn_js, cdn_widg=cdn_widg, cdn_css=cdn_css)


if __name__ == "__main__":
    app.run()
