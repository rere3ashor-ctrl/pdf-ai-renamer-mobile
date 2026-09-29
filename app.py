import os,re,json,base64
from flask import Flask,render_template,request,jsonify
import requests,fitz
app=Flask(__name__)
MODEL=os.getenv("GEMINI_MODEL","gemini-3.5-flash-lite")
app.config["MAX_CONTENT_LENGTH"]=25*1024*1024
def safe(s):
 s=re.sub(r'[<>:"/\\|?*\x00-\x1f]','',(s or '').strip()); return re.sub(r'\s+',' ',s).strip(" .-")[:150]
def analyze(b):
 key=os.getenv("GEMINI_API_KEY","").strip()
 if not key: raise RuntimeError("مفتاح Gemini غير مضبوط على الخادم")
 doc=fitz.open(stream=b,filetype="pdf")
 parts=[{"text":"اقرأ المستند الإداري العربي. أعد JSON فقط: subject موضوع مختصر، applicant اسم صاحب الطلب إن وجد وإلا فارغ، date تاريخ المستند الرئيسي DD-MM-YYYY، confidence high أو medium أو low. لا تستخدم تاريخ مرفق ثانوي ولا تخمن."}]
 for i in range(min(2,len(doc))):
  pix=doc[i].get_pixmap(dpi=120,alpha=False)
  parts.append({"inline_data":{"mime_type":"image/png","data":base64.b64encode(pix.tobytes("png")).decode()}})
 doc.close()
 schema={"type":"OBJECT","properties":{"subject":{"type":"STRING"},"applicant":{"type":"STRING"},"date":{"type":"STRING"},"confidence":{"type":"STRING"}},"required":["subject","applicant","date","confidence"]}
 r=requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",headers={"x-goog-api-key":key,"Content-Type":"application/json"},json={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.1,"responseMimeType":"application/json","responseSchema":schema}},timeout=90)
 if not r.ok: raise RuntimeError(r.json().get("error",{}).get("message","خطأ من Gemini"))
 o=json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
 bits=[safe(o.get("subject")) or "مستند"]
 if safe(o.get("applicant")): bits.append(safe(o.get("applicant")))
 if safe(o.get("date")): bits.append(safe(o.get("date")))
 return {"filename":safe(" - ".join(bits))+".pdf","confidence":o.get("confidence","low")}
@app.get("/")
def home(): return render_template("index.html")
@app.post("/analyze")
def api():
 f=request.files.get("file")
 if not f or not f.filename.lower().endswith(".pdf"): return jsonify(error="اختاري ملف PDF صحيح"),400
 try:return jsonify(analyze(f.read()))
 except Exception as e:return jsonify(error=str(e)),500
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))
