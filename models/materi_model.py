import datetime
from database import fetch_all, fetch_one, execute, new_id, utcnow_iso, json_dumps, as_bool, as_int
from services.supabase_storage import delete_file

MATERIALS="materials"; ACCESS="material_access"; PROGRESS="material_progress"

def _decode_material(d):
    if not d: return None
    d=dict(d)
    if not d.get("tipe"): d["tipe"]="pdf" if d.get("pdf_url") else "rangkuman"
    d["urutan_bab"]=as_int(d.get("urutan_bab"),1); d["urutan_subbab"]=as_int(d.get("urutan_subbab"),1)
    return d

def _decode_access(d):
    if not d: return None
    d=dict(d); d["view_count"]=as_int(d.get("view_count"),0)
    return d

def _decode_progress(d):
    if not d: return None
    d=dict(d); d["completed"]=as_bool(d.get("completed"),False); return d

def _validate_upload(pdf_url,pdf_path,pdf_filename):
    if not pdf_url or not pdf_path or not pdf_filename or not str(pdf_filename).lower().endswith('.pdf'):
        raise ValueError("Upload PDF belum selesai atau file bukan PDF.")

def _validate_rangkuman_gambar(url,path):
    if not url or not path: raise ValueError("Upload gambar rangkuman belum selesai.")

def create_material(jenjang,kelas,mapel,judul,pdf_url,pdf_path,pdf_filename,ringkasan="",bab="Bab 1",urutan_bab=1,urutan_subbab=1,tipe="pdf",rangkuman_gambar_url=None,rangkuman_gambar_path=None):
    tipe=(tipe or "pdf").strip()
    if tipe=="rangkuman":
        _validate_rangkuman_gambar(rangkuman_gambar_url,rangkuman_gambar_path); pdf_url=pdf_path=pdf_filename=None
    else:
        tipe="pdf"; _validate_upload(pdf_url,pdf_path,pdf_filename); rangkuman_gambar_url=rangkuman_gambar_path=None
    try: urutan_bab=int(urutan_bab or 1)
    except (TypeError,ValueError): urutan_bab=1
    try: urutan_subbab=int(urutan_subbab or 1)
    except (TypeError,ValueError): urutan_subbab=1
    mid=new_id(); now=utcnow_iso()
    execute("""INSERT INTO materials (id,jenjang,kelas,mapel,bab,urutan_bab,urutan_subbab,judul,tipe,ringkasan,pdf_url,pdf_path,pdf_filename,rangkuman_gambar_url,rangkuman_gambar_path,created_at,updated_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (mid,jenjang,str(kelas),mapel,(bab or "Bab 1").strip(),urutan_bab,urutan_subbab,judul,tipe,ringkasan,pdf_url,pdf_path,pdf_filename,rangkuman_gambar_url,rangkuman_gambar_path,now,now))
    return get_material(mid)

def get_material(material_id): return _decode_material(fetch_one("SELECT * FROM materials WHERE id=? LIMIT 1", (material_id,)))
def get_all_materials():
    out=[_decode_material(x) for x in fetch_all("SELECT * FROM materials")]
    return sorted(out,key=lambda x:(x.get("jenjang", ""),x.get("kelas", ""),x.get("mapel", ""),x.get("judul", "")))
def get_materials_for_user(user): return [m for m in get_all_materials() if m.get("jenjang")==str(user.get("jenjang") or "") and str(m.get("kelas"))==str(user.get("kelas") or "")]

def get_subject_groups_for_user(user):
    mats=get_materials_for_user(user); groups={}
    for m in mats: groups.setdefault(m.get("mapel") or "Lainnya",[]).append(m)
    out=[]
    for mapel,items in groups.items():
        bab_map={}
        for m in items: bab_map.setdefault(m.get("bab") or "Bab 1",[]).append(m)
        bab_list=[]
        for bab,subs in bab_map.items():
            subs.sort(key=lambda x:(int(x.get("urutan_subbab",1) or 1),str(x.get("judul") or "")))
            urutan=min(int(x.get("urutan_bab",1) or 1) for x in subs)
            bab_list.append({"nama":bab,"urutan":urutan,"subbab":subs})
        bab_list.sort(key=lambda x:(x["urutan"],x["nama"]))
        out.append({"mapel":mapel,"jumlah_bab":len(bab_list),"jumlah_subbab":sum(len(x["subbab"]) for x in bab_list),"bab":bab_list})
    out.sort(key=lambda x:x["mapel"]); return out

def get_bab_for_user(user,mapel,bab):
    for g in get_subject_groups_for_user(user):
        if g["mapel"]==mapel:
            for b in g["bab"]:
                if b["nama"]==bab: return b
    return None

def update_material(material_id,pdf_url=None,pdf_path=None,pdf_filename=None,rangkuman_gambar_url=None,rangkuman_gambar_path=None,tipe=None,**fields):
    material=get_material(material_id)
    if not material: raise ValueError("Materi tidak ditemukan.")
    tipe=(tipe or material.get("tipe") or "pdf").strip(); fields["tipe"]=tipe
    if tipe=="rangkuman":
        if rangkuman_gambar_url or rangkuman_gambar_path:
            _validate_rangkuman_gambar(rangkuman_gambar_url,rangkuman_gambar_path); delete_file(material.get("rangkuman_gambar_path")); fields.update({"rangkuman_gambar_url":rangkuman_gambar_url,"rangkuman_gambar_path":rangkuman_gambar_path})
        if material.get("pdf_path"): delete_file(material.get("pdf_path")); fields.update({"pdf_url":None,"pdf_path":None,"pdf_filename":None})
    else:
        if pdf_url or pdf_path or pdf_filename:
            _validate_upload(pdf_url,pdf_path,pdf_filename); delete_file(material.get("pdf_path")); fields.update({"pdf_url":pdf_url,"pdf_path":pdf_path,"pdf_filename":pdf_filename})
        if material.get("rangkuman_gambar_path"): delete_file(material.get("rangkuman_gambar_path")); fields.update({"rangkuman_gambar_url":None,"rangkuman_gambar_path":None})
    fields["updated_at"]=utcnow_iso()
    allowed={k for k in fields if k in {"jenjang","kelas","mapel","bab","urutan_bab","urutan_subbab","judul","tipe","ringkasan","pdf_url","pdf_path","pdf_filename","rangkuman_gambar_url","rangkuman_gambar_path","updated_at","isi"}}
    fields={k:fields[k] for k in allowed};
    if not fields:return
    sql="UPDATE materials SET "+", ".join(f"{k}=?" for k in fields)+" WHERE id=?"
    execute(sql, tuple(fields[k] for k in fields)+(material_id,))

def delete_material(material_id):
    material=get_material(material_id)
    if material:
        delete_file(material.get("pdf_path")); delete_file(material.get("rangkuman_gambar_path"))
    execute("DELETE FROM materials WHERE id=?", (material_id,))

def _access_id(user_id,material_id): return f"{user_id}_{material_id}"
def has_access(user,material_id): return fetch_one("SELECT id FROM material_access WHERE id=? LIMIT 1", (_access_id(user["id"],material_id),)) is not None

def grant_access(user_id,material_id,source="kuota"):
    aid=_access_id(user_id,material_id); now=utcnow_iso(); old=fetch_one("SELECT * FROM material_access WHERE id=?",(aid,))
    if old:
        execute("UPDATE material_access SET source=?,updated_at=? WHERE id=?",(source,now,aid))
    else:
        execute("INSERT INTO material_access (id,user_id,material_id,source,created_at,updated_at,view_count) VALUES (?,?,?,?,?,?,?)",(aid,user_id,material_id,source,now,now,0))

def revoke_access(user_id,material_id): execute("DELETE FROM material_access WHERE id=?",(_access_id(user_id,material_id),))
def get_access_map_for_user(user_id): return {x.get("material_id"):_decode_access(x) for x in fetch_all("SELECT * FROM material_access WHERE user_id=?",(user_id,))}

def record_material_view(user_id,material_id):
    aid=_access_id(user_id,material_id); data=fetch_one("SELECT * FROM material_access WHERE id=?",(aid,))
    if not data:return False
    now=utcnow_iso(); count=as_int(data.get("view_count"),0)+1; first=data.get("first_accessed_at") or now
    execute("UPDATE material_access SET first_accessed_at=?,last_accessed_at=?,view_count=?,updated_at=? WHERE id=?",(first,now,count,now,aid)); return True

def mark_progress(user_id,material_id,completed=True):
    pid=_access_id(user_id,material_id); now=utcnow_iso(); old=fetch_one("SELECT id FROM material_progress WHERE id=?",(pid,))
    if old: execute("UPDATE material_progress SET completed=?,updated_at=? WHERE id=?",("true" if completed else "false",now,pid))
    else: execute("INSERT INTO material_progress (id,user_id,material_id,completed,updated_at) VALUES (?,?,?,?,?)",(pid,user_id,material_id,"true" if completed else "false",now))

def get_progress_for_user(user_id): return {x.get("material_id"):_decode_progress(x) for x in fetch_all("SELECT * FROM material_progress WHERE user_id=?",(user_id,))}

def delete_user_material_data(user_id):
    execute("DELETE FROM material_access WHERE user_id=?",(user_id,)); execute("DELETE FROM material_progress WHERE user_id=?",(user_id,))
