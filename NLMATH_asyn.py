# -*- coding: utf-8 -*-
"""
Created on Tue May 30 11:22:10 2023

@author: lnico
"""

#BOUTspeed

def boutspeed(dfexpt):
    import pandas as pd
    import numpy as np

    dfr = dfexpt.iloc[:,2:]
    velp = pd.DataFrame()
    for v2 in range(3,len(dfr.columns),5): #change this number if you add more parameters
        velp = pd.concat([velp, dfr.iloc[:,v2], dfr.iloc[:,v2+1]], axis = 1)

    velplst = []
    gentype = []

    for n in velp.columns[::2]:
        velplst.append(n.split("_")[-1])
        gentype.append(n.rsplit(" ", 1)[0])

    newspeed = pd.DataFrame()

    for n,k in zip(velplst, gentype):
        newspeed[k + " BSpeed_" + n] = [np.nan]*len(velp)
        newspeed.loc[(velp[k + " Pausecount_" + n] ==0), [k + " BSpeed_" + n]] = velp[k + " Velocity_" + n]

    newspeed = pd.concat([dfexpt.iloc[:,0:2], newspeed], axis = 1)

    return newspeed

def bspeed(dfexpt, dfwt):
    import pandas as pd
    import numpy as np
    df_se = velodabest(dfexpt, "Expt", "BSpeed")
    df_sw = velodabest(dfwt, "WT", "BSpeed")

    fgt6=pd.DataFrame()
    fgt6 = pd.concat([df_se, df_sw]).reset_index(drop=False)
    fgt6['genre'] = fgt6['ExperimentState'] + " " + fgt6['Type']

    return fgt6

#overall speed

def ospeed(dfwt, dfexpt):
    import pandas as pd

    df_se = velodabest(dfexpt, "Expt", "Velocity")
    df_sw = velodabest(dfwt, "WT", "Velocity")

    fgt6=pd.DataFrame()
    fgt6 = pd.concat([df_se, df_sw]).reset_index(drop=False)
    fgt6['genre'] = fgt6['ExperimentState'] + " " + fgt6['Type']

    return fgt6

#straightness index calculations

def straightnessindexmeter(dft, genre):
    import pandas as pd
    import numpy as np

    phase = ['First phase', 'Second phase', 'Third phase']

    dfstraighttotal = pd.DataFrame()

    for x in phase:
        df_x = dft[(dft['ExperimentState']== str(x))]
        t1 = distpersec(df_x).iloc[:,2:]
        t2 = disppersec(df_x).iloc[:,2:]
        v = t1.values/t2.values
        straightnessindex = pd.DataFrame(v, index=t1.index, columns=t1.columns).replace(np.inf, np.nan)
        sim = pd.DataFrame(data = straightnessindex.mean(axis=0), columns = ['averagestraightnessindex'])
        sim['ExperimentState'] = x
        sim["Type"]= genre
        sim['genre']= str(x)+ " " + str(genre)
        dfstraighttotal = pd.concat([dfstraighttotal, sim], axis = 0)
    return dfstraighttotal.reset_index(drop=False)

def disppersec(dftest):
    import pandas as pd
    import numpy as np
    import math
    distancevelo  = dftest.filter(regex='X_.*|Y_.*|Fall_.*')
    dfdist = pd.concat([round(dftest['Seconds'],1), distancevelo], axis =1)
    listsecondsnumber = list(range(int(dftest['Seconds'].iloc[0]),math.floor(dftest['Seconds'].iloc[-1])))
    df_sumdisp = pd.DataFrame()

    for n in listsecondsnumber:
        arraylist = list(np.linspace(n,n+1,6))
        df_sumdisp = pd.concat([df_sumdisp, sectioneddispchunks(arraylist, dfdist)], axis = 0).reset_index(drop=True)

    df_sumdisp = df_sumdisp.shift(periods=1)
    tempsecondslist = dftest.iloc[::5, 0:2].reset_index(drop=True)
    df_sumdisp = pd.concat([tempsecondslist, df_sumdisp], axis = 1).reset_index(drop=True)

    return df_sumdisp

# for dispplacement per sec
def sectioneddispchunks(chunklist, dfdist):
    import pandas as pd
    import numpy as np

    sliced = pd.DataFrame()
    for nn in chunklist:
        nnum = round(nn,1)
        sliced = pd.concat([sliced, dfdist[dfdist['Seconds'] ==nnum]], axis = 0)

    df_slice = pd.DataFrame()

    test = sliced.iloc[:,1:]
    for v2 in range(0,len(test.columns),3):
        dfnewt4= pd.DataFrame()
        naming = (test.iloc[:,v2]).name
        arraynum = naming.split("_")[-1]
        dfnewt4 = pd.concat([test.iloc[:,v2], test.iloc[:,v2+1]], axis = 1)
        if sum(test.iloc[:,v2+2])==0.0: #accounting if there is a fall, do not calculate displacement for that moment
            linalg_variable = np.linalg.norm(dfnewt4.diff(axis=0), axis=1)
            if np.nansum(linalg_variable) < 1.0:  #if sum of displacement events is less than 0, do not want
                df_slice["Disp_" + str(arraynum)] = np.nan
            else:
                df_slice["Disp_" + str(arraynum)] = linalg_variable
        else:
            df_slice["Disp_" + str(arraynum)] = np.nan

    df_slice2 = df_slice.sum(axis=0).to_frame().T
    return df_slice2

#distance per sec

def distpersec (dfexpt):
    import pandas as pd
    import numpy as np

    dfnewt = dfexpt.iloc[::5,:].reset_index(drop=True)
    dfnewt.drop(dfnewt.filter(regex='Fall_.*|Velocity_.*|Pausecount_.*').columns, axis=1, inplace=True)

    dfnewt3 = dfnewt.iloc[:,2:].copy()
    distsec = pd.DataFrame()
    for v2 in range(0,len(dfnewt3.columns),2):
        dfnewt4= pd.DataFrame()
        #assining name
        naming = (dfnewt3.iloc[:,v2]).name
        arraynum = naming.split("_")[-1]

        dfnewt4 = pd.concat([dfnewt3.iloc[:,v2], dfnewt3.iloc[:,v2+1]], axis = 1)
        distsec["Dist_" + str(arraynum)] = np.linalg.norm(dfnewt4.diff(axis=0), axis=1)
    distsec = pd.concat([dfnewt.iloc[:,0:2], distsec], axis = 1).reset_index(drop=True)

    return distsec

def totalheight(dfexpt, dfwt):

    awt5 = refine(dfexpt, dfwt, "Y")
    awt5['genre'] = awt5['ExperimentState'] + " " + awt5['Type']

    return awt5

def refine(dfexpt, dfwt, phrase):
    import pandas as pd

    phaselist = ['First phase', 'Second phase', 'Third phase']
    filterword = phrase + ".*"

    awt5 = pd.DataFrame()
    for df, typeo in zip([dfexpt, dfwt], ["Expt", "WT"]):
        awtb = pd.DataFrame()
        for n in phaselist:
            filtereddf = df[(df['ExperimentState']== n)].filter(regex=filterword)

            match phrase:
                case "Y":
                    result = getattr(filtereddf, "mean")(axis=0)
                case "Fall":
                    result = getattr(filtereddf, "sum")(axis=0)/1

            awt = pd.DataFrame()
            awt[phrase] = result
            awt['ExperimentState'] = n
            awtb = pd.concat([awtb, awt])

        awtb = awtb.reset_index()
        awtb["Type"] = typeo
        awt5 = pd.concat([awt5, awtb])

    return awt5

def meangraph(df):
    import pandas as pd
    phase = ['First phase','Second phase', 'Third phase']
    dft = pd.DataFrame()
    for n in phase:
        df1 = df[(df["ExperimentState"] == n)].reset_index(drop=True)
        df_meand = pd.DataFrame()
        df_meand['Seconds']=df1['Seconds']
        df_meand['ExperimentState'] = n
        df_meand['mean']= df1.iloc[:,2:].mean(axis=1)
        df_meand['CI']= df1.iloc[:,2:].sem(axis=1)*1.96
        dft = pd.concat([dft, df_meand])
    return dft

def fallcalc(df, phase):
    import pandas as pd

    dff = df.filter(regex="Fall.*")
    dff = pd.concat([df.iloc[:,0:2], dff], axis=1)
    dff2 = dff[(dff["ExperimentState"] == phase)].reset_index(drop=True)
    nnumber = len(dff2.iloc[:,2:].columns)
    dff2["Total falls per sec"] = (dff2.iloc[:,2:].sum(axis=1))/nnumber

    return dff2

def velodabest(df, typeo, keyword):
    import pandas as pd
    #typeo is either WT or EXPT
    keywordnew = keyword +".*"

    phase = ["First phase", "Second phase", "Third phase"]
    fgt2b = pd.DataFrame()
    for n in phase:
        dfsed = calcgraph(df, keywordnew)
        df_ff = dfsed[(dfsed['ExperimentState']== n)]
        fgt = pd.DataFrame()
        fgt[keyword]= df_ff.iloc[:,2:].mean(axis=0)
        fgt["ExperimentState"] = n
        fgt2b = pd.concat([fgt2b, fgt])

    fgt2b["Type"] = typeo

    if any(fgt2b[keyword].isnull()):
        value = fgt2b[fgt2b[keyword].isnull()].index.tolist()[0]
        fgt2b = fgt2b.drop(index= value)

    return fgt2b

def calcgraph(df, filterword):
    import pandas as pd

    phase = ["First phase", "Second phase", "Third phase"]
    df4 = pd.DataFrame()
    for n in phase:
        df_sd = df[(df["ExperimentState"] == n)].reset_index(drop=True)
        df_time = pd.DataFrame()
        df_time['Seconds'] = df_sd['Seconds']

        df_sd2 = df_sd.filter(regex=filterword)
        df_time["ExperimentState"] = n
        df_sd2 = abs(df_sd2)
        df_sd3 = pd.concat([df_time, df_sd2], axis=1)
        df4 = pd.concat([df4, df_sd3])

    return df4
