import numpy as np
import pandas as pd

'''=====================================
       SECTION: CHART OF AVAILABLE ATTRIBUTES
       ====================================='''
    test = relevantFacilities
    relevantParent = [facilities[facilities['facilityid'] == facil]['ParentRecAreaID'].values[0] for facil in relevantFacilities]
    popularattributes = ['Pets Allowed', 'Checkin Time', 'Campfire Allowed']

    facilattr = pd.read_csv('./data/facilattriblist.csv')
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
    popularnotavailable = [x for x in popularattributes if x not in relevantattributes]
    popularnotavailablestr = ', '.join(popularnotavailable).title()

    # first will setup basic df with relevant facilities
    heatdfA = pd.DataFrame(np.array(test), columns=['facilityid'])

    # now want to add columns via relevant activities and an array of the values
    for col in relevantattributes:
        values = []
        for facil in relevantParent:
            if col in facilattrsub[facilattrsub['facilityid'] == facil]['attriblist'].values[0]:
                if col not in popularattributes:
                    values.append(1)
                else:
                    values.append(2)
            else:
                values.append(0)
        heatdfA[col] = values

    # change from facilityid to rec area and drop any duplicates that emerge
    for index, row in heatdfA.iterrows():
        facil = row['facilityid']
        recarea = facilities[facilities['ParentRecAreaID'] == facil]['RecAreaName'].values[0]
        heatdfA.iloc[index, 0] = recarea
    heatdfA = heatdfA.drop_duplicates(subset=['facilityid'])

    # now the bokeh heat map
    heatdfA = heatdfA.set_index("facilityid")
    heatdfA.columns.name = 'attributes'
    heatdfAstack = pd.DataFrame(heatdfA.stack(), columns=['value']).reset_index()
    sourceA = ColumnDataSource(heatdfAstack)

    colors = ["#FFFFFF", "#D2D7CE", "#3f5335"]
    mapper = LinearColorMapper(palette=colors, low=0, high=2)

    ppA = figure(sizing_mode="stretch_width", plot_height=500, title="Available and Popular Attributes",
                 y_range=list(heatdfA.index), x_range=list(reversed(heatdfA.columns)),
                 toolbar_location=None, tools="", x_axis_location="above")

    ppA.rect(y="facilityid", x="attributes", width=1, height=1, source=sourceA,
             line_color='grey', fill_color=transform('value', mapper))

    ppA.xaxis.major_label_orientation = math.pi / 4

    # unpack bokeh figure
    script3, div3 = components(ppA)