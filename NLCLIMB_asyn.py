# -*- coding: utf-8 -*-
"""
Created on Sat Sep  3 23:17:03 2022

@author: lnico
"""

def removenans(df):
    perc = 50.0
    min_count =  int(((100-perc)/100)*df.shape[0] + 1)
    df = df.dropna(axis=1, thresh=min_count)

    return df

def onlycolsneeded(df):
    cols = [col for col in df if col.endswith('X') or col.endswith('Y')]
    df = df.loc[:,cols]

    return df

def gridding(df, phase, fps, fn):
    import numpy as np

    ca = 1/fps

    dfp = df[df['ExperimentState'] == phase].iloc[1:].reset_index(drop = True)
    dfp['RealSeconds'] = dfp['Seconds'] - dfp['Seconds'].iloc[0]

    gaps = dfp['RealSeconds'].diff().shift(-1)

    anchor = None
    for i in range(0,4):
        if ca*0.75 <= gaps.iloc[i] <= ca*1.25:
            anchor = i
            break

    if anchor is None:
        raise Exception("No consistent 0.2 s gap in the first 5 rows of " + phase + " in " + fn)

    ta = dfp['RealSeconds'].iloc[anchor]
    shift = np.floor(ta/ca + 0.5 - 1e-9)*ca - ta

    dfp['RealSeconds'] = dfp['RealSeconds'] + shift
    dfp['Box'] = np.floor(dfp['RealSeconds']/ca + 0.5 - 1e-9)
    dfp['Offset'] = np.abs(dfp['RealSeconds'] - dfp['Box']*ca)

    dfp = dfp[(dfp['Box'] >= 0) & (dfp['Box'] <= fps*30 - 1)]
    dfp = dfp.sort_values('Offset').groupby('Box').head(1)
    dfp = dfp.set_index('Box').reindex(range(fps*30)).reset_index(drop = True)

    return dfp

def reassembly(results, results3, fps, fn):
    import pandas as pd

    results2 = pd.DataFrame()

    df_first = gridding(results, 'First phase', fps, fn)
    df_second = gridding(results, 'Second phase', fps, fn)
    df_third = gridding(results, 'Third phase', fps, fn)

    results2 = pd.concat([df_first, df_second, df_third]).reset_index(drop = True)
    results2 = removenans(results2)
    results2 = onlycolsneeded(results2)
    results3 = pd.concat([results3, results2], axis = 1).reset_index(drop = True)

    return results3

def fivefps(dfs, fps, fns):
    import pandas as pd
    import numpy as np

    results3 = pd.DataFrame()
    results4 = pd.DataFrame()
    df_time = pd.DataFrame()
    df_time['Seconds'] = np.tile(np.arange(0,30,1/fps), 3)

    for df, fn in zip(dfs, fns):
        results3 = reassembly(df, results3, fps, fn)

    results4 = pd.concat([df_time, results3], axis=1)

    return results4

def cleanup(results4, fps, genotype):

    ly = []
    ly.extend(['First phase' for i in range(fps*30)])
    ly.extend(['Second phase' for i in range(fps*30)])
    ly.extend(['Third phase' for i in range(fps*30)])

    newElements=[*range(1,1000,1)]
    results4.columns = [genotype +' X' + '_' + str(newElements.pop(0)) if "X" in col else col for col in results4.columns]

    newElements=[*range(1,1000,1)] #needs a second one
    results4.columns = [genotype +' Y' + '_' + str(newElements.pop(0)) if "Y" in col else col for col in results4.columns]

    results4.insert(1, 'ExperimentState', ly)
    #pixel conversion
    results4.iloc[:,2:] = results4.iloc[:,2:]*0.14

    return results4

def compilation(filename, genotype):
    import pandas as pd
    import os

    dfs=[]
    fns=[]
    fps = 5

    for file_no, k in zip(os.listdir(filename), range(0,200)):
        if file_no.lower().endswith(".csv"):
            f = os.path.join(filename, file_no)
            df=pd.read_csv(f)
            dfs.append(df)
            fns.append(file_no)

    df_t = fivefps(dfs, fps, fns)
    df_t = cleanup(df_t, fps, genotype)

    return df_t, fps

def fallso(df):
    import pandas as pd
    import numpy as np

    df0 = df.filter(regex="Y.*")
    fall2=pd.DataFrame()
    frontrow = df.iloc[:,0:2]

    for n,k in zip(df0.columns, range(1,len(df0.columns)+1)):
        kk = str(k)
        fa = str(n.rsplit(" ", 1)[0])
        fallo = pd.DataFrame()
        fallo['Diff_' + kk] = df0[n] - df0[n].shift(1)
        fallo[fa + ' Fall_'+ kk ] = 0
        fallo.loc[(fallo['Diff_'+ kk ]<-3.17),[fa + ' Fall_'+ kk]] = 1   # threshold derived from confusion matrix on 2025-12-26
        fallo.loc[(fallo['Diff_'+ kk ].isnull()),[fa + ' Fall_'+ kk]] = np.nan
        fall2 = pd.concat([fall2, fallo], axis = 1)

    fall2 = pd.concat([frontrow, fall2], axis=1)

    return fall2

def speedcalc(df, fps):
    import pandas as pd
    import numpy as np

    indices = list(range(1,len(df.columns),2))
    rows = list(range(0,len(df)-1))
    df_disp = pd.DataFrame()

    for i,kk in zip(indices, range(1,len(indices)+1)):  #parsing through each object
        displacement_list =[]
        temp = pd.DataFrame()
        k = str(kk)
        naming = df.iloc[:,i].name#series name
        nama = naming.rsplit(" ", 1)[0]

        for ii in rows: #parsing through each line in column
            x1_D = df.iloc[ii,i] #0,1
            y1_D = df.iloc[ii,i+1] #0,2
            x2_D = df.iloc[ii+1,i] #1,1
            y2_D = df.iloc[ii+1,i+1] #1,2
            displacement = abs((((x2_D-x1_D)**2) + ((y2_D-y1_D)**2))**0.5)   #is actually speed
            displacement_list.append(displacement)
        temp[nama + " Velocity_" + k]= displacement_list
        df_disp = pd.concat([df_disp, temp], axis=1).reset_index(drop=True)


    ca = 1/fps

    df_disp.iloc[:,:] = df_disp.iloc[:,:]/ca

    df3 = pd.DataFrame([[np.nan] * len(df_disp.columns)], columns=df_disp.columns)
    df2 = pd.concat([df3, df_disp], ignore_index=True)

    df2['Seconds'] = df['Seconds'].reset_index(drop=True)
    return df2

def pausing(df):
    import pandas as pd
    import numpy as np

    ss = df.filter(regex="Velocity.*").reset_index(drop=True)
    dfp = pd.DataFrame()

    for n, k in zip(ss.columns, range(1,len(ss.columns)+1)):
            k = str(k)
            nama = n.rsplit(" ", 1)[0]
            dfp[nama + ' Pausecount_' + k] = [0]*len(ss)
            dfp.loc[(ss[n]<2.588),[nama + ' Pausecount_' + k]]= 1  # threshold derived from confusion matrix on 2025-12-26
            dfp.loc[(ss[n].isnull()),[nama + ' Pausecount_' + k]]= np.nan

    return dfp

def separation (df, phase):

    phase_X_Y= df[(df['ExperimentState']== phase)].drop(df.columns[[1]],axis = 1)

    return phase_X_Y

def generation(df, genotype):
    import pandas as pd
    import numpy as np
    import re
    from natsort import index_natsorted

    fps = 5
    firstphase_len = fps*30 #length of phase
    phase = ['First phase', 'Second phase', 'Third phase']

    consolidateddf = pd.DataFrame()
    dfftot2 = pd.DataFrame()
    df_speedtot = pd.DataFrame()
    df_pausetot = pd.DataFrame()

    for n in phase:
        dff = df[(df['ExperimentState'] == n)]
        df_speed = speedcalc(separation(df, n), fps)

        consolidateddf = pd.concat([consolidateddf, dff])
        dfftot2 = pd.concat([dfftot2, fallso(dff)])
        df_speedtot = pd.concat([df_speedtot, df_speed])
        df_pausetot = pd.concat([df_pausetot, pausing(df_speed)])

    consolidateddf = consolidateddf.reset_index(drop=True)
    dfftot3 = dfftot2.filter(regex = "Fall.*").reset_index(drop=True)
    dfst6 = df_speedtot.drop(["Seconds"], axis =1).reset_index(drop=True)
    df_pausetot = df_pausetot.reset_index(drop=True)

    dffnew = pd.DataFrame()
    dffnew = pd.concat([dffnew, consolidateddf], axis=1)
    dffnew = pd.concat([dffnew, dfftot3], axis=1)
    dffnew = pd.concat([dffnew, dfst6], axis=1)
    dffnew = pd.concat([dffnew, df_pausetot], axis =1)

    heading2 = dffnew.iloc[:,2:].columns
    lstp2 = []
    pdf2 = pd.DataFrame()
    for n2 in range(0,len(heading2)):
        lstp2.append(int(re.search(r'(?<=_)\d+', heading2[n2]).group()))
    pdf2['Headings']=heading2
    pdf2['num'] = lstp2
    pdff2= pdf2.sort_values(by='num', key=lambda x: np.argsort(index_natsorted(pdf2["num"]))).reset_index(drop=True)
    dffn = dffnew.iloc[:,2:]
    dfr = dffn.reindex(columns = pdff2['Headings'])
    for v2 in range(2,len(dfr.columns),5): #change this number if you add more parameters
        for v1 in range(0,len(dfr)):
            if dfr.iloc[v1,v2]>= 1:
                dfr.iloc[v1,v2+1] = np.nan
    first2 = dffnew.iloc[:,0:2]
    dftotalexpt = pd.concat([first2, dfr],axis=1)

    #removing tracking errors
    chunk = len(dftotalexpt.iloc[:,2:].columns)/5  #change this number if you add more parameters
    dfowo = pd.DataFrame()
    for n in np.hsplit(dftotalexpt.iloc[:,2:],chunk):
        #if velocity exceeds 80
        dfstp = n.filter(regex="Velocity.*")
        output = dfstp[(dfstp > 80)].count()

        temp = pd.DataFrame()
        hug = dfstp.iloc[0:firstphase_len]
        temp['Acc'] = abs(hug.diff())/(1/fps)
        output2 = temp[(temp < 0.04)].count()

        #if there are dead flies
        yval = n.filter(regex="Y.*")
        dfstp2 = yval.iloc[0:firstphase_len]
        output3 = dfstp2[(dfstp2 < 20)].count().values

        if int(output.iloc[0]) <3 and int(output2.iloc[0]) < int(firstphase_len/6) and int(output3[0]) < int(firstphase_len/3) :
            dfowo=pd.concat([dfowo,n], axis=1)

    dfowo = pd.concat([dftotalexpt.iloc[:,0:2], dfowo], axis = 1)

    return dfowo
