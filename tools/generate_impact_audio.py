"""Author deterministic original impact layers; project license not selected."""
from pathlib import Path
import hashlib,json,math,wave
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'game/assets/audio/impact'
SOURCE=ROOT/'art_source/production/impact_audio'
RATE=44100
SEED=71031
PEAK=.58
SWING_LEADS={'swing_heavy':.20,'swing_charged':.28}
PROFILES={
 'light':[('contact_tick',-18),('metal_light',-18)],
 'heavy':[('contact_tick',-17),('metal_heavy',-15),('body_thump',-14),('debris_tail',-25)],
 'charged':[('contact_tick',-17),('metal_heavy',-13),('body_thump',-15),('charge_sub',-18),('debris_tail',-23)],
 'blocked_metal':[('contact_tick',-22),('metal_block',-13),('debris_tail',-28)]}

def lowpass(x,cutoff):
    alpha=1-math.exp(-math.tau*cutoff/RATE);out=np.empty_like(x);value=0.
    for i,sample in enumerate(x):value+=alpha*(sample-value);out[i]=value
    return out

def encode(path,samples):
    pcm=np.rint(samples*32767).astype('<i2')
    with wave.open(str(path),'wb') as stream:
        stream.setparams((2,2,RATE,0,'NONE','not compressed'));stream.writeframes(pcm.tobytes())
    return pcm.astype(float)/32767

def main():
    OUT.mkdir(parents=True,exist_ok=True);SOURCE.mkdir(parents=True,exist_ok=True)
    definitions=[('contact_tick',.065),('metal_light',.22),('metal_heavy',.33),('body_thump',.18),('charge_sub',.32),('debris_tail',.42),('metal_block',.29),('swing_heavy',.25),('swing_charged',.31)]
    rendered={};records=[]
    for index,(name,duration) in enumerate(definitions):
        rng=np.random.default_rng(SEED+index);t=np.arange(round(duration*RATE))/RATE;noise=rng.uniform(-1,1,len(t));x=np.zeros(len(t));onset=np.minimum(1,t/.0015)
        if name=='contact_tick':
            high=noise-lowpass(noise,1800);x=(high*.7+np.sin(math.tau*(2700*t-1000*t*t))*.15)*np.exp(-t/0.012)*onset
        elif name in ['metal_light','metal_heavy','metal_block']:
            modes={'metal_light':[1217,1743,2377,3821],'metal_heavy':[417,683,1031,1709,2927],'metal_block':[1103,1903,2711,3911]}[name]
            for n,f in enumerate(modes):x+=np.sin(math.tau*f*t+rng.uniform(-.5,.5))*np.exp(-t/(.055+.025*(len(modes)-n)))/(n+2)
            x=(x+noise*np.exp(-t/.008)*.22)*onset
        elif name in ['body_thump','charge_sub']:
            start,end,fall=(135,55,.025) if name=='body_thump' else (90,38,.055)
            phase=math.tau*(end*t+(start-end)*fall*(1-np.exp(-t/fall)))
            x=(np.sin(phase)+.22*np.sin(phase*2.03)+lowpass(noise,320)*.9)*np.exp(-t/(.048 if name=='body_thump' else .095))*onset
        elif name=='debris_tail':
            high=lowpass(noise,7200)-lowpass(noise,1200)
            for _ in range(19):
                start=rng.uniform(.008,.27);env=np.where(t>=start,np.exp(-np.maximum(0,t-start)/rng.uniform(.003,.012)),0)
                x+=high*env*rng.uniform(.15,.45)*(1-start/.35)
            x+=lowpass(noise,700)*np.exp(-t/.12)*.1
        else:
            mid=lowpass(noise,4800)-lowpass(noise,160);envelope=np.sin(np.pi*t/duration)**1.4
            x=mid*envelope*(.8+.2*np.sin(math.tau*27*t))
            if name=='swing_charged':x+=lowpass(noise,240)*envelope*.5
        x-=x.mean();x*=np.minimum(1,(duration-t)/.008)
        # Very small independent side tail gives width without smearing onset.
        delay=round(.00045*RATE);side=np.r_[np.zeros(delay),x[:-delay]]
        stereo=np.column_stack([x, x*.94+side*.06]);stereo*=PEAK/max(1e-12,np.abs(stereo).max())
        # Playback starts with the attack, while baked silence aligns the air
        # acceleration with that attack's startup. No deferred engine callback.
        lead=SWING_LEADS.get(name,0.)
        if lead:stereo=np.concatenate([np.zeros((round(lead*RATE),2)),stereo])
        path=OUT/(name+'.wav');decoded=encode(path,stereo);rendered[name]=decoded
        amplitude=abs(decoded).max(axis=1);nonzero=np.flatnonzero(amplitude>0)
        records.append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'frames':len(decoded),'seconds':len(decoded)/RATE,'sound_body_seconds':duration,'quiet_lead_seconds':lead,'first_nonzero_pcm_seconds':float(nonzero[0]/RATE) if len(nonzero) else None,'designed_envelope_peak_seconds':lead+duration/2 if name in SWING_LEADS else None,'measured_waveform_peak_seconds':float(np.argmax(amplitude)/RATE),'seed':SEED+index,'peak':float(amplitude.max()),'rms':float(np.sqrt(np.mean(decoded**2))),'dc':decoded.mean(0).tolist()})
    profile_reports={};sequence=[];timeline=[];time=0.
    for name,layers in PROFILES.items():
        length=max(len(rendered[key]) for key,_ in layers);mix=np.zeros((length,2))
        for key,db in layers:mix[:len(rendered[key])]+=rendered[key]*10**((db-1.5)/20)
        peak=float(abs(mix).max());assert peak<.8
        profile_reports[name]={'layers':[{'key':k,'db':d} for k,d in layers],'sum_peak_at_zero_density':peak,'global_group_headroom_db':-1.5}
        timeline.append({'profile':name,'start_seconds':time,'duration':length/RATE});sequence.extend([mix,np.zeros((round(.35*RATE),2))]);time+=(length/RATE)+.35
    audition=ROOT/'build/art-review/impact-audio/audition.wav';audition.parent.mkdir(parents=True,exist_ok=True);encode(audition,np.concatenate(sequence))
    manifest={'license':'not-selected','license_scope':'New original project audio; no third-party samples; repository owner has not selected a redistribution license.','authorship':'Original deterministic oscillator, filtered-noise and inharmonic-resonator DSP authored for RUNEFALL','generator':'tools/generate_impact_audio.py','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'numpy_version':np.__version__,'rng':'numpy.random.default_rng/PCG64','rate_hz':RATE,'channels':2,'pcm_bits':16,'base_seed':SEED,'individual_peak_target':PEAK,'files':records,'profiles':profile_reports,'attack_start_timeline':{'heavy':{'asset':'swing_heavy','quiet_lead_seconds':.20,'sound_body_seconds':.25,'designed_envelope_peak_seconds':.325,'end_seconds':.45,'playback_pitch':1.0},'charged_heavy':{'asset':'swing_charged','quiet_lead_seconds':.28,'sound_body_seconds':.31,'designed_envelope_peak_seconds':.435,'end_seconds':.59,'playback_pitch':1.0},'clock_scope':'Baked timing is relative to attack-start playback at pitch1. Audio follows the mixer clock, and does not freeze with presentation hitpause. Stop_all still cancels playback; no delayed timer/async work is added.'},'audition':{'path':str(audition.relative_to(ROOT)),'timeline':timeline,'sha256':hashlib.sha256(audition.read_bytes()).hexdigest()},'scope':'Offline generation/peak verification only; actual mix/listening/Web playback and combat AV review separate'}
    (SOURCE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'files':len(records),'total_bytes':sum(r['bytes'] for r in records),'profile_peaks':{k:v['sum_peak_at_zero_density'] for k,v in profile_reports.items()},'audition':str(audition)},indent=2))

if __name__=='__main__':main()
