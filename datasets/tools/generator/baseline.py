import pandas as pd, json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline, make_union
from sklearn.metrics import f1_score, accuracy_score
d=pd.read_csv('nlp/farmer_queries.csv',encoding='utf-8-sig')
tr,va,te=[d[d.split==s] for s in ('train','validation','test')]
feat=make_union(TfidfVectorizer(analyzer='char_wb',ngram_range=(2,5),sublinear_tf=True,min_df=2),
                TfidfVectorizer(analyzer='word',ngram_range=(1,2),sublinear_tf=True))
m=make_pipeline(feat,LogisticRegression(max_iter=3000,C=10,class_weight='balanced'))
X=lambda df:(df.text+' || '+df.normalized_text)
m.fit(X(tr),tr.intent)
res={}
for n,df in (('validation',va),('test',te)):
    p=m.predict(X(df)); res[n]=dict(accuracy=round(accuracy_score(df.intent,p),3),macro_f1=round(f1_score(df.intent,p,average='macro'),3))
te=te.assign(pred=m.predict(X(te)), ok=lambda x: x.intent==x.pred)
res['test_by_language']=te.groupby('language').ok.mean().round(3).to_dict()
res['test_by_noise']=te.groupby('noise_type').ok.mean().round(3).to_dict()
res['ood_recall_test']=round(te[te.intent=='out_of_domain'].ok.mean(),3)
res['worst_intents_test']=te.groupby('intent').ok.mean().round(2).sort_values().head(8).to_dict()
json.dump(res,open('reports/baseline_tfidf_logreg.json','w'),indent=1)
print(json.dumps(res,indent=1))
