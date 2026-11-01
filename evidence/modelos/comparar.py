import json, os, shutil, subprocess, time, urllib.request
from pathlib import Path
models=Path(os.environ['DOC_ASSISTANT_MODELS_DIR'])
exe=os.environ.get('DOC_ASSISTANT_LLAMA_SERVER') or shutil.which('llama-server')
if not exe: raise SystemExit('Falta llama-server en PATH o DOC_ASSISTANT_LLAMA_SERVER')
tests=[('En el manual ficticio: alcance 4 m. Responde solo con el alcance.', '4 m'),('En la ficha ficticia: tensión 24 V. Responde solo con la tensión.', '24 V'),('En el manual ficticio no se indica ningún precio. ¿Qué precio indica? Responde que no está indicado.', 'no')]
for model in ['Qwen3.5-4B-Q4_K_M.gguf','Qwen3.5-9B-Q4_K_M.gguf']:
    print('modelo',model,flush=True)
    with open(os.devnull, 'w') as f:
        p=subprocess.Popen([exe,'-m',str(models/model),'--host','127.0.0.1','--port','8181','-c','8192','-np','2','--reasoning-budget','0'],stdout=f,stderr=subprocess.STDOUT)
    print('pid',p.pid,flush=True)
    try:
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            if p.poll() is not None: raise RuntimeError(f'servidor terminó {p.returncode}')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8181/health',timeout=2) as r:
                    if r.status==200: break
            except OSError: time.sleep(1)
        else: raise RuntimeError('timeout')
        print('rss_kib_carga',subprocess.check_output(['ps','-o','rss=','-p',str(p.pid)],text=True).strip(),flush=True)
        for question,expected in tests:
            body=json.dumps({'model':'local','messages':[{'role':'user','content':question}],'temperature':0,'max_tokens':48}).encode()
            req=urllib.request.Request('http://127.0.0.1:8181/v1/chat/completions',body,{'Content-Type':'application/json'})
            t=time.monotonic()
            with urllib.request.urlopen(req,timeout=120) as r: result=json.load(r)
            answer=result['choices'][0]['message']['content'].strip()
            print('segundos',round(time.monotonic()-t,2),'esperado',repr(expected),'respuesta',repr(answer),flush=True)
        print('rss_kib_final',subprocess.check_output(['ps','-o','rss=','-p',str(p.pid)],text=True).strip(),flush=True)
    finally:
        if p.poll() is None:
            p.terminate()
            try: p.wait(timeout=15)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
        print('cerrado',p.pid,p.returncode,flush=True)
