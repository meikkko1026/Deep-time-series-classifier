#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  5 11:46:56 2020

@author: bhossein
"""
from sklearn import tree

from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
import joblib
import pandas as pd
import xlsxwriter

#%% 
X, y = make_classification(n_samples=1000, n_features=4,
                            n_informative=2, n_redundant=0,
                            random_state=0, shuffle=False)
n_estimators = 4
clf = RandomForestClassifier(n_estimators = n_estimators, max_depth=17, random_state=0)
clf.fit(X, y)
RandomForestClassifier(...)
print(clf.predict([[0, 0, 0, 0]]))
count = 0
for i in range(n_estimators):
    count += clf.estimators_[i].tree_.node_count
    print(clf.estimators_[i].tree_.node_count)
print(count) 
a = clf.estimators_[2]  
#tree.plot_tree(a) 


save_name= 'rf9_nf_cv1.p'
result_dir = 'results/'
rf_model = joblib.load(result_dir+save_name, mmap_mode='r')

df1 = pd.DataFrame(a,
                   columns=['features', 'threshold','child_left','child_right'])
df1 = pd.DataFrame(list(a),
                   columns=['features', 'threshold','child_left','child_right'])

columns=['features', 'threshold','child_left','child_right']
with xlsxwriter.Workbook('test.xlsx') as workbook:
    for i_tr in range(len(rf_model)):
        worksheet = workbook.add_worksheet(name = 'tree'+str(i_tr))
        worksheet.write_row(0,0, columns)
        tree_data = rf_model[i_tr]
        for row_num, data in enumerate(tree_data):
            worksheet.write_column(1,row_num, data)