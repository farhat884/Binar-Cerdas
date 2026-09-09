import datetime
from firebase_config import db
from services.supabase_storage import delete_file

MATERIALS="materials"; ACCESS="material_access"; PROGRESS="material_progress"

def _doc(doc):
    d=doc.to_dict(); d["id"]=doc.id; return d

def _validate_upload(pdf_url,pdf_path,pdf_filename):
    if not pdf_url or not pdf_path or not pdf_filename or not str(pdf_filename).lower().endswith('.pdf'):
        raise ValueError("Upload PDF belum selesai atau file bukan PDF.")

def create_material(jenjang,kelas,mapel,judul,pdf_url,pdf_path,pdf_filename,ringkasan=""):
    _validate_upload(pdf_url,pdf_path,pdf_filename)
    ref=db.collection(MATERIALS).document(); data={"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"judul":judul,"ringkasan":ringkasan,"pdf_url":pdf_url,"pdf_path":pdf_path,"pdf_filename":pdf_filename,"created_at":datetime.datetime.utcnow(),"updated_at":datetime.datetime.utcnow()}
    ref.set(data); data["id"]=ref.id; return data

def get_material(material_id):
    doc=db.collection(MATERIALS).document(material_id).get(); return _doc(doc) if doc.exists else None

def get_all_materials():
    out=[_doc(d) for d in db.collection(MATERIALS).stream()]; return sorted(out,key=lambda x:(x.get("jenjang",""),x.get("kelas",""),x.get("mapel",""),x.get("judul","")))

def get_materials_for_user(user):
    return [m for m in get_all_materials() if m.get("jenjang")==str(user.get("jenjang") or "") and str(m.get("kelas"))==str(user.get("kelas") or "")]

def update_material(material_id,pdf_url=None,pdf_path=None,pdf_filename=None,**fields):
    material=get_material(material_id)
    if not material: raise ValueError("Materi tidak ditemukan.")
    if pdf_url or pdf_path or pdf_filename:
        _validate_upload(pdf_url,pdf_path,pdf_filename)
        delete_file(material.get("pdf_path")); fields.update({"pdf_url":pdf_url,"pdf_path":pdf_path,"pdf_filename":pdf_filename})
    fields["updated_at"]=datetime.datetime.utcnow(); db.collection(MATERIALS).document(material_id).update(fields)

def delete_material(material_id):
    material=get_material(material_id)
    if material: delete_file(material.get("pdf_path"))
    db.collection(MATERIALS).document(material_id).delete()

def _access_id(user_id,material_id): return f"{user_id}_{material_id}"
def has_access(user,material_id): return db.collection(ACCESS).document(_access_id(user["id"],material_id)).get().exists
def grant_access(user_id,material_id,source="kuota"): db.collection(ACCESS).document(_access_id(user_id,material_id)).set({"user_id":user_id,"material_id":material_id,"source":source,"created_at":datetime.datetime.utcnow()})
def revoke_access(user_id,material_id): db.collection(ACCESS).document(_access_id(user_id,material_id)).delete()
def get_access_map_for_user(user_id): return {d.to_dict().get("material_id"):d.to_dict() for d in db.collection(ACCESS).where("user_id","==",user_id).stream()}
def mark_progress(user_id,material_id,completed=True): db.collection(PROGRESS).document(_access_id(user_id,material_id)).set({"user_id":user_id,"material_id":material_id,"completed":bool(completed),"updated_at":datetime.datetime.utcnow()},merge=True)
def get_progress_for_user(user_id): return {d.to_dict().get("material_id"):d.to_dict() for d in db.collection(PROGRESS).where("user_id","==",user_id).stream()}