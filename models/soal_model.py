import datetime
from firebase_config import db
COLLECTION="questions"; ATTEMPTS="quiz_attempts"

def _doc(doc): d=doc.to_dict(); d["id"]=doc.id; return d

def create_question(jenjang,kelas,mapel,tipe,pertanyaan,pilihan,jawaban_benar,penjelasan="",material_id=None):
    ref=db.collection(COLLECTION).document(); data={"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"tipe":tipe,"material_id":material_id,"pertanyaan":pertanyaan,"pilihan":pilihan,"jawaban_benar":jawaban_benar,"penjelasan":penjelasan,"created_at":datetime.datetime.utcnow()}; ref.set(data); data["id"]=ref.id; return data

def get_question(qid):
    d=db.collection(COLLECTION).document(qid).get(); return _doc(d) if d.exists else None

def get_questions(**filters):
    out=[]
    for d in db.collection(COLLECTION).stream():
        x=_doc(d)
        if all(str(x.get(k) or "")==str(v) for k,v in filters.items() if v not in (None,"")): out.append(x)
    return sorted(out,key=lambda x:str(x.get("created_at") or ""))

def update_question(qid, **fields): db.collection(COLLECTION).document(qid).update(fields)
def delete_question(qid): db.collection(COLLECTION).document(qid).delete()

def save_attempt(user_id,tipe,jenjang,kelas,mapel,score,total,answers):
    ref=db.collection(ATTEMPTS).document(); data={"user_id":user_id,"tipe":tipe,"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"score":score,"total":total,"percent":round(score/total*100,2) if total else 0,"answers":answers,"created_at":datetime.datetime.utcnow()}; ref.set(data); data["id"]=ref.id; return data

def get_attempts(user_id):
    out=[_doc(d) for d in db.collection(ATTEMPTS).where("user_id","==",user_id).stream()]
    return sorted(out,key=lambda x:str(x.get("created_at") or ""),reverse=True)
