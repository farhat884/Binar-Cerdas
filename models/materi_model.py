import datetime
from firebase_config import db
from services.supabase_storage import delete_file

MATERIALS="materials"; ACCESS="material_access"; PROGRESS="material_progress"

def _doc(doc):
    d=doc.to_dict(); d["id"]=doc.id
    # Materi lama belum punya field "tipe" -> anggap "pdf" kalau ada file PDF,
    # kalau enggak anggap "rangkuman" (biar tetap tampil dengan benar di UI baru).
    if not d.get("tipe"):
        d["tipe"]="pdf" if d.get("pdf_url") else "rangkuman"
    return d

def _validate_upload(pdf_url,pdf_path,pdf_filename):
    if not pdf_url or not pdf_path or not pdf_filename or not str(pdf_filename).lower().endswith('.pdf'):
        raise ValueError("Upload PDF belum selesai atau file bukan PDF.")

def _validate_rangkuman_gambar(url,path):
    if not url or not path:
        raise ValueError("Upload gambar rangkuman belum selesai.")

def create_material(jenjang,kelas,mapel,judul,pdf_url,pdf_path,pdf_filename,ringkasan="",bab="Bab 1",urutan_bab=1,urutan_subbab=1,tipe="pdf",rangkuman_gambar_url=None,rangkuman_gambar_path=None):
    tipe=(tipe or "pdf").strip()
    if tipe=="rangkuman":
        _validate_rangkuman_gambar(rangkuman_gambar_url,rangkuman_gambar_path)
        pdf_url=pdf_path=pdf_filename=None
    else:
        tipe="pdf"
        _validate_upload(pdf_url,pdf_path,pdf_filename)
        rangkuman_gambar_url=rangkuman_gambar_path=None
    try: urutan_bab=int(urutan_bab or 1)
    except (TypeError,ValueError): urutan_bab=1
    try: urutan_subbab=int(urutan_subbab or 1)
    except (TypeError,ValueError): urutan_subbab=1
    bab=(bab or "Bab 1").strip()
    ref=db.collection(MATERIALS).document(); data={"jenjang":jenjang,"kelas":str(kelas),"mapel":mapel,"bab":bab,"urutan_bab":urutan_bab,"urutan_subbab":urutan_subbab,"judul":judul,"tipe":tipe,"ringkasan":ringkasan,"pdf_url":pdf_url,"pdf_path":pdf_path,"pdf_filename":pdf_filename,"rangkuman_gambar_url":rangkuman_gambar_url,"rangkuman_gambar_path":rangkuman_gambar_path,"created_at":datetime.datetime.utcnow(),"updated_at":datetime.datetime.utcnow()}
    ref.set(data); data["id"]=ref.id; return data

def get_material(material_id):
    doc=db.collection(MATERIALS).document(material_id).get(); return _doc(doc) if doc.exists else None

def get_all_materials():
    out=[_doc(d) for d in db.collection(MATERIALS).stream()]; return sorted(out,key=lambda x:(x.get("jenjang",""),x.get("kelas",""),x.get("mapel",""),x.get("judul","")))

def get_materials_for_user(user):
    return [m for m in get_all_materials() if m.get("jenjang")==str(user.get("jenjang") or "") and str(m.get("kelas"))==str(user.get("kelas") or "")]

def get_subject_groups_for_user(user):
    """Kelompok materi menjadi mata pelajaran -> bab -> subbab."""
    mats=get_materials_for_user(user)
    groups={}
    for m in mats:
        mapel=m.get("mapel") or "Lainnya"
        groups.setdefault(mapel,[]).append(m)
    out=[]
    for mapel, items in groups.items():
        bab_map={}
        for m in items:
            bab=m.get("bab") or "Bab 1"
            bab_map.setdefault(bab,[]).append(m)
        bab_list=[]
        for bab, subs in bab_map.items():
            subs.sort(key=lambda x:(int(x.get("urutan_subbab",1) or 1),str(x.get("judul") or "")))
            urutan=min(int(x.get("urutan_bab",1) or 1) for x in subs)
            bab_list.append({"nama":bab,"urutan":urutan,"subbab":subs})
        bab_list.sort(key=lambda x:(x["urutan"],x["nama"]))
        out.append({"mapel":mapel,"jumlah_bab":len(bab_list),"jumlah_subbab":sum(len(x["subbab"]) for x in bab_list),"bab":bab_list})
    out.sort(key=lambda x:x["mapel"])
    return out

def get_bab_for_user(user,mapel,bab):
    groups=get_subject_groups_for_user(user)
    for g in groups:
        if g["mapel"]==mapel:
            for b in g["bab"]:
                if b["nama"]==bab: return b
    return None

def update_material(material_id,pdf_url=None,pdf_path=None,pdf_filename=None,rangkuman_gambar_url=None,rangkuman_gambar_path=None,tipe=None,**fields):
    material=get_material(material_id)
    if not material: raise ValueError("Materi tidak ditemukan.")
    tipe=(tipe or material.get("tipe") or "pdf").strip()
    fields["tipe"]=tipe
    if tipe=="rangkuman":
        if rangkuman_gambar_url or rangkuman_gambar_path:
            _validate_rangkuman_gambar(rangkuman_gambar_url,rangkuman_gambar_path)
            delete_file(material.get("rangkuman_gambar_path"))
            fields.update({"rangkuman_gambar_url":rangkuman_gambar_url,"rangkuman_gambar_path":rangkuman_gambar_path})
        if material.get("pdf_path"):
            delete_file(material.get("pdf_path")); fields.update({"pdf_url":None,"pdf_path":None,"pdf_filename":None})
    else:
        if pdf_url or pdf_path or pdf_filename:
            _validate_upload(pdf_url,pdf_path,pdf_filename)
            delete_file(material.get("pdf_path")); fields.update({"pdf_url":pdf_url,"pdf_path":pdf_path,"pdf_filename":pdf_filename})
        if material.get("rangkuman_gambar_path"):
            delete_file(material.get("rangkuman_gambar_path")); fields.update({"rangkuman_gambar_url":None,"rangkuman_gambar_path":None})
    fields["updated_at"]=datetime.datetime.utcnow(); db.collection(MATERIALS).document(material_id).update(fields)

def delete_material(material_id):
    material=get_material(material_id)
    if material: delete_file(material.get("pdf_path"))
    db.collection(MATERIALS).document(material_id).delete()

def _access_id(user_id,material_id): return f"{user_id}_{material_id}"
def has_access(user,material_id): return db.collection(ACCESS).document(_access_id(user["id"],material_id)).get().exists
def grant_access(user_id,material_id,source="kuota"):
    now=datetime.datetime.utcnow()
    ref=db.collection(ACCESS).document(_access_id(user_id,material_id))
    snap=ref.get()
    if snap.exists:
        ref.set({"user_id":user_id,"material_id":material_id,"source":source,"updated_at":now},merge=True)
    else:
        ref.set({"user_id":user_id,"material_id":material_id,"source":source,"created_at":now,"updated_at":now,"view_count":0})
def revoke_access(user_id,material_id): db.collection(ACCESS).document(_access_id(user_id,material_id)).delete()
def get_access_map_for_user(user_id): return {d.to_dict().get("material_id"):d.to_dict() for d in db.collection(ACCESS).where("user_id","==",user_id).stream()}
def record_material_view(user_id,material_id):
    """Catat bahwa siswa benar-benar membuka halaman materi.
    Dibuat terpisah dari grant_access karena akses bisa diberikan admin tanpa
    berarti siswa sudah membaca materi."""
    now=datetime.datetime.utcnow()
    ref=db.collection(ACCESS).document(_access_id(user_id,material_id))
    snap=ref.get()
    if not snap.exists:
        return False
    data=snap.to_dict() or {}
    count=int(data.get("view_count",0) or 0)+1
    update={"last_accessed_at":now,"view_count":count,"updated_at":now}
    if not data.get("first_accessed_at"):
        update["first_accessed_at"]=now
    ref.set(update,merge=True)
    return True

def mark_progress(user_id,material_id,completed=True): db.collection(PROGRESS).document(_access_id(user_id,material_id)).set({"user_id":user_id,"material_id":material_id,"completed":bool(completed),"updated_at":datetime.datetime.utcnow()},merge=True)
def get_progress_for_user(user_id): return {d.to_dict().get("material_id"):d.to_dict() for d in db.collection(PROGRESS).where("user_id","==",user_id).stream()}

def delete_user_material_data(user_id):
    """Hapus semua data akses & progress materi milik satu siswa. Dipanggil
    saat admin menghapus akun siswa, biar gak nyisain dokumen yatim di
    koleksi material_access/material_progress yang nunjuk ke user_id yang
    udah gak ada."""
    for d in db.collection(ACCESS).where("user_id","==",user_id).stream():
        d.reference.delete()
    for d in db.collection(PROGRESS).where("user_id","==",user_id).stream():
        d.reference.delete()