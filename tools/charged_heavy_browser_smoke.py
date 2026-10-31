"""Actual CDP-touch charged whiff/contact slice; no game-state mutation.

Run through check_mobile_web.py --phase charged-heavy-focus. This narrow gate
does not replace desktop/mobile full journeys, persistence, or target-device
normal-speed audiovisual review.
"""
import asyncio
import math
import os
from pathlib import Path
import shutil
import tempfile
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.async_api import async_playwright

from mobile_browser_smoke import MobileRun, PORTRAIT, UI_TIMEOUT


CONTACT_TIMELINE_JS = """a => {
    const row={armed_at:performance.now(),setup_timeout_ms:60000,rows:[],last_frame:-1,
        baseline_count:a.count,target_id:a.target,heavy_pointer:a.pointer};
    window.__RUNEFALL_CHARGED_CONTACT_OBS=row;
    const released=event=>{
        if(event.isTrusted && Array.from(event.changedTouches).some(t=>t.identifier===a.pointer)){
            row.release_at=performance.now();
            document.removeEventListener('touchend',released,true);
        }
    };
    document.addEventListener('touchend',released,true);
    function poll(){
        const now=performance.now(),s=window.__RUNEFALL_STATE;
        if(now-row.armed_at>=row.setup_timeout_ms){
            row.expired=true;document.removeEventListener('touchend',released,true);return;
        }
        if(s && s.physics_frame!==row.last_frame){
            row.last_frame=s.physics_frame;
            const enemy=s.enemy_art.find(e=>e.id===a.target);
            row.rows.push({at:now,frame:s.physics_frame,x:s.x,z:s.z,health:s.health,
                stagger:s.stagger,charge_elapsed:s.charge_elapsed,hit_pause:s.hit_pause,
                state:s.hero_art.state,attack:structuredClone(s.attack),impact_count:s.impact.count,
                stick:structuredClone(s.touch.stick_vector),pressed:[...s.touch.pressed_actions],
                target:enemy?{id:enemy.id,x:enemy.x,z:enemy.z,health:enemy.health,
                    state:enemy.state,sampled_time:enemy.sampled_time,stagger:enemy.stagger}:null});
            if(row.rows.length>96)row.rows.shift();
            if(row.release_at!==undefined && !row.snapshot &&
                s.impact.history.some(e=>e.sequence>a.count && e.source==='player' &&
                    e.attack_id==='charged_heavy' && e.target_id===a.target) && enemy?.state==='heavy_hit'){
                row.snapshot=structuredClone(s);row.matched_at=now;
                document.removeEventListener('touchend',released,true);return;
            }
        }
        requestAnimationFrame(poll);
    }
    requestAnimationFrame(poll);
}"""


async def arm_contact_timeline(qa,count,target,pointer):
    # Only our bounded observer metadata is written. Game snapshots and input
    # remain untouched, and the first matched packet is retained on failure.
    async with asyncio.timeout(UI_TIMEOUT/1000):
        await qa.page.evaluate(CONTACT_TIMELINE_JS,{'count':count,'target':target,'pointer':pointer})


async def save_contact_timeline(qa):
    try:
        async with asyncio.timeout(10):
            diagnostic=await qa.page.evaluate('structuredClone(window.__RUNEFALL_CHARGED_CONTACT_OBS)')
        if diagnostic is not None:qa.write('charged-heavy-release-timeline.json',diagnostic)
    except Exception as error:
        qa.write('charged-heavy-release-timeline-diagnostic.json',{'error':str(error)})


async def release_into_contact(qa,pointer):
    started=time.monotonic()
    try:
        async with asyncio.timeout(UI_TIMEOUT/1000):
            await qa.touch.end(pointer)
            row=await qa.page.evaluate("""() => new Promise(resolve=>{
                function poll(){const row=window.__RUNEFALL_CHARGED_CONTACT_OBS;
                    if(row.snapshot || row.expired || (row.release_at!==undefined &&
                        performance.now()-row.release_at>=15000))resolve(structuredClone(row));
                    else requestAnimationFrame(poll);
                }poll();})""")
            assert 'snapshot' in row and 'release_at' in row,row
            assert 0<=row['matched_at']-row['release_at']<UI_TIMEOUT,row
        qa.latest=row['snapshot']
        qa.action_observations.append({'stage':qa.stage,'predicate':'prearmed charged receipt and actual heavy_hit',
            'seconds':round(time.monotonic()-started,3),'matched_ms':row['matched_at']-row['release_at'],
            'snapshot':row['snapshot']})
        qa.write('mobile-action-observations.json',qa.action_observations)
        return row['snapshot']
    finally:
        # Diagnostic reads after a timeout never turn that timeout into a pass.
        # Retaining the page row also survives cancellation of its response RPC.
        await save_contact_timeline(qa)


def length(vector):
    assert isinstance(vector,list) and len(vector)==3 and all(isinstance(v,(int,float)) and math.isfinite(v) for v in vector),vector
    return math.sqrt(sum(v*v for v in vector))


def segment_distance(point,start,end):
    length(point);length(start);length(end)
    delta=[b-a for a,b in zip(start,end)]
    denominator=sum(value*value for value in delta)
    assert denominator>0, (start,end)
    fraction=max(0,min(1,sum((p-a)*d for p,a,d in zip(point,start,delta))/denominator))
    return math.sqrt(sum((p-a-fraction*d)**2 for p,a,d in zip(point,start,delta)))


def validate_contact(event):
    assert event['source']=='player' and event['attack_id']=='charged_heavy' and event['strength']=='charged',event
    assert event['attack_instance_id']>0 and event['target_id']>0,event
    assert not event['blocked'] and not event['killed'],event
    assert abs(event['amount']-69.3)<.01,event
    assert abs(event['health_before']-event['health_after']-event['amount'])<.01,event
    assert event['reaction']=='heavy_hit' and abs(event['reaction_duration']-.48)<.001,event
    for field in ['hitstop','attacker_pause','victim_pause']:
        assert abs(event[field]-.075)<.001,(field,event)
    assert abs(event['requested_recoil_m']-.35)<.001,event
    for field in ['normal','direction']:
        assert abs(length(event[field])-1)<.003,(field,event)
    assert event['contact_source'] in ['hurtbox_ray','hurtbox_proxy'],event
    assert 0<=event['contact_phase']<=1,event
    # Contact, frozen gameplay, and presentation share the sampled substep
    # clock. A later processing-tick time must not replace the query time.
    query_time=.34+.18*event['contact_phase']
    assert abs(event['attack_elapsed']-query_time)<.0001,event
    grip,tip=event['contact_blade_grip'],event['contact_blade_tip']
    assert abs(length([b-a for a,b in zip(grip,tip)])-1.19)<.003,event
    distance=segment_distance(event['point'],grip,tip)
    # This audits the reported physical sample, not resource reach metadata.
    assert distance<=.125,('point outside .12m blade capsule plus5mm tolerance',distance,event)
    return {'point_to_blade_segment_m':distance,'blade_grip_to_tip_m':length([b-a for a,b in zip(grip,tip)]),
        'query_sample_time_s':query_time,'packet_attack_elapsed_s':event['attack_elapsed']}


def validate_frozen_contact(snapshot):
    # An observer may copy a later frame after the brief hitstop. Packet
    # clocks are always checked above; this additionally audits a genuinely
    # frozen pair when one is actually present in the copied snapshot.
    if snapshot['hit_pause']<=0 or snapshot['attack']['attack_id']!='charged_heavy':
        return {'observed':False,'reason':'copied snapshot outside charged attacker hitstop'}
    attack=snapshot['attack']
    events=[event for event in snapshot['impact']['history'] if event['source']=='player'
        and event['attack_id']=='charged_heavy' and event['attack_instance_id']==attack['attack_instance_id']]
    assert events,('frozen strike has no matching confirmed receipt',snapshot)
    event=max(events,key=lambda item:item['sequence'])
    art=snapshot['hero_art']
    assert art['state']=='charged_heavy',art
    assert abs(attack['attack_elapsed']-event['attack_elapsed'])<.001,(attack,event)
    assert abs(art['sampled_time']-event['attack_elapsed'])<.001,(art,event)
    grip,tip=art['blade_grip_world'],art['blade_tip_world']
    assert abs(length([b-a for a,b in zip(grip,tip)])-1.19)<.003,art
    distance=segment_distance(event['point'],grip,tip)
    assert distance<=.125,('contact outside actual frozen drawn blade capsule',distance,snapshot)
    trail=art['blade_trail']
    assert trail['visible'] and trail['samples']>=2 and trail['triangles']>=2,trail
    return {'observed':True,'sequence':event['sequence'],'attack_instance_id':event['attack_instance_id'],
        'packet_attack_elapsed_s':event['attack_elapsed'],'gameplay_attack_elapsed_s':attack['attack_elapsed'],
        'render_sampled_time_s':art['sampled_time'],'point_to_actual_drawn_segment_m':distance,
        'blade_trail':trail}


async def run(url,output,phase='charged-heavy-focus',rotation_driver='playwright'):
    assert phase=='charged-heavy-focus' and rotation_driver=='playwright'
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    for pattern in ['charged-heavy-*','mobile-*']:
        for path in output.glob(pattern):
            if path.is_file() and path.name!='mobile-export-context.json':path.unlink()
    qa=MobileRun(output)
    qa.write('charged-heavy-result.json',{'outcome':'running','scope':'Unverified focused current run'})
    qa.write('charged-heavy-scope.json',{'scope':'Actual fresh mobile Chromium/CDP touch whiff, fully charged contact and reaction only; no full-journey, target-device or AAA audiovisual approval',
        'ui_timeout_ms':UI_TIMEOUT,'navigation_timeout_seconds':60,'navigation_final_distance_m':1.2,
        'input':'Genuine CDP touch; readonly HUD/impact histories; no teleport, injected action, forced sync or save write'})
    parts=urlsplit(url);query=dict(parse_qsl(parts.query));query['qa']='1'
    test_url=urlunsplit(parts._replace(query=urlencode(query)))
    options={'headless':True,'viewport':PORTRAIT,'device_scale_factor':2,'is_mobile':True,'has_touch':True,
        'args':['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']}
    executable=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium')
    if executable:options['executable_path']=executable
    context=None
    try:
        async with async_playwright() as playwright:
            with tempfile.TemporaryDirectory(prefix='.runefall-heavy-profile-',dir=output.resolve().parent) as profile:
                context=await playwright.chromium.launch_persistent_context(profile,**options)
                try:
                    await qa.bind(context,context.pages[0]);qa.mark('charged_heavy_title')
                    await qa.ready(test_url)
                    await qa.tap_button('새로운 서약');await qa.wait('s.started && s.modal')
                    await qa.tap_button('성역으로 향한다');before=await qa.stable()
                    assert {'count','spawn_count','history'}<=set(before['impact']),before
                    baseline=(before['impact']['count'],before['impact']['spawn_count'])
                    qa.mark('charged_heavy_whiff')
                    heavy=await qa.touch_action('heavy',hold=True)
                    await qa.wait("s.charge_elapsed>=.65 && s.hero_art.state==='charge'")
                    whiff_pose=await qa.observe_action("s.hero_art.state==='charged_heavy'",None,lambda:qa.touch.end(heavy))
                    attack=whiff_pose['attack']
                    assert attack['attack_id']=='charged_heavy',attack
                    assert abs(attack['attack_duration']-1.06)<.001,attack
                    assert abs(attack['attack_startup']-.34)<.001 and abs(attack['attack_active']-.18)<.001,attack
                    assert abs(attack['attack_duration']-attack['attack_startup']-attack['attack_active']-.54)<.001,attack
                    await qa.record('charged-heavy-whiff-pose',status=whiff_pose)
                    after=await qa.idle()
                    for _ in range(2):after=await qa.next_state(after)
                    assert after['encounter']==-1 and not after['dead'],after
                    assert (after['impact']['count'],after['impact']['spawn_count'])==baseline,after
                    await qa.record('charged-heavy-whiff-no-burst',screenshot=True,status=after)

                    qa.mark('charged_heavy_real_approach')
                    await qa.navigate(0,-17)
                    approach=await qa.idle()
                    assert approach['encounter']==-1 and approach['z']>-19.5,approach
                    heavy=await qa.touch_action('heavy',hold=True)
                    await qa.wait("s.charge_elapsed>=.65 && s.hero_art.state==='charge'")
                    # Charge stays held while the player walks through the
                    # actual first gate. Both pointers retain real ownership.
                    stick=await qa.stick((0,-.95))
                    await qa.wait("s.encounter===0 && s.z< -20.5 && !s.dead")
                    await qa.touch.end(stick)
                    await qa.touch_action('lock_on')
                    locked=await qa.wait("s.locked && s.enemy_art.some(e=>e.id===s.locked_target_id && e.kind==='melee' && !e.elite && !e.boss && !e.dead)")
                    target_id=locked['locked_target_id']
                    await qa.record('charged-heavy-locked-approach',status=locked)
                    box,sx,sy=await qa.canvas(locked)
                    generation=locked['touch']['layout_generation']
                    center=locked['touch']['joystick_center'];radius=locked['touch']['joystick_radius']
                    def css_point(point):
                        return box['x']+point[0]*sx,box['y']+point[1]*sy
                    # Let the target approach in finite UI observations. This
                    # is the normal enemy motor, never a QA position command.
                    async with asyncio.timeout(60):
                        while True:
                            current=await qa.state()
                            assert current['touch']['layout_generation']==generation,current
                            target=next(e for e in current['enemy_art'] if e['id']==target_id)
                            distance=math.hypot(current['x']-target['x'],current['z']-target['z'])
                            if distance<=7:break
                            await qa.wait("s.enemy_art.some(e=>e.id===a.id && Math.hypot(s.x-e.x,s.z-e.z)<=a.distance)",{'id':target_id,'distance':max(7,distance-3)})
                    before_contact=await qa.state()
                    count=before_contact['impact']['count'];spawns=before_contact['impact']['spawn_count']
                    assert (count,spawns)==baseline,before_contact
                    qa.mark('charged_heavy_recovery_setup')

                    # Prepare the observer before taking a genuine incoming
                    # hit. Center the stick and use the enemy's real recovery
                    # rather than racing an RPC against its initial windup.
                    await arm_contact_timeline(qa,count,target_id,heavy)
                    advancing=await qa.touch.start(*css_point(center))
                    try:
                        async with asyncio.timeout(60):
                            await qa.touch.move(advancing,*css_point((center[0],center[1]-.35*radius)))
                            await qa.wait("s.enemy_art.some(e=>e.id===a && Math.hypot(s.x-e.x,s.z-e.z)<=2.4)",target_id)
                            await qa.touch.move(advancing,*css_point(center))
                            recovery=await qa.wait("s.health<a && s.health>0 && !s.dead && s.stagger<=0 && s.charge_elapsed>=.65 && s.hero_art.state==='charge' && Math.hypot(...s.touch.stick_vector)<.01 && s.touch.pressed_actions.includes('heavy')",before_contact['health'])
                            await qa.record('charged-heavy-real-incoming-hit-recovery',status=recovery)
                        qa.mark('charged_heavy_actual_contact')
                        contact=await release_into_contact(qa,heavy)
                    finally:
                        await qa.touch.end(advancing)
                    events=[event for event in contact['impact']['history'] if event['sequence']>count and event['source']=='player' and event['attack_id']=='charged_heavy']
                    assert events,contact
                    victim=next(e for e in contact['enemy_art'] if e['id']==target_id)
                    assert victim['mode']=='skeletal' and victim['profile']=='sentinel_melee',victim
                    assert victim['weapon_attached'] and abs(victim['grip_to_tip_m']-1.19)<.003,victim
                    checks=[validate_contact(event) for event in events]
                    frozen_contact=validate_frozen_contact(contact)
                    await qa.record('charged-heavy-contact',status=contact)
                    await qa.idle()
                    settled=await qa.wait("s.enemy_art.some(e=>e.id===a && Math.hypot(e.recoil_displacement[0],e.recoil_displacement[2])>.001)",target_id)
                    target=next(e for e in settled['enemy_art'] if e['id']==target_id)
                    recoil=math.hypot(target['recoil_displacement'][0],target['recoil_displacement'][2])
                    assert recoil<=.355 and abs(target['recoil_requested_m']-.35)<.001,target
                    await qa.touch_action('pause')
                    final=await qa.wait("s.paused && s.modal && !s.dead && s.health>0")
                    new_events=[event for event in final['impact']['history'] if event['sequence']>count]
                    charged_events=[event for event in new_events if event['source']=='player' and event['attack_id']=='charged_heavy']
                    pairs=[(event['attack_instance_id'],event['target_id']) for event in charged_events]
                    assert pairs and len(pairs)==len(set(pairs)),('duplicate same-strike target impact',charged_events)
                    assert len({event['attack_instance_id'] for event in charged_events})==1,charged_events
                    assert final['impact']['count']-count==len(new_events),final
                    assert final['impact']['spawn_count']-spawns==len(new_events),final
                    for event in charged_events:validate_contact(event)
                    await qa.record('charged-heavy-contact-paused',screenshot=True,status=final)
                    observation=await qa.page.evaluate('structuredClone(window.__RUNEFALL_MOBILE_TOUCH_OBS)')
                    assert observation['trusted'] and observation['max_points']>=2,observation
                    assert not qa.errors,qa.errors
                    qa.write('charged-heavy-proof.json',{'scope':'Actual input/cumulative confirmed receipts and skeletal reaction; screenshots may follow the sampled short impact. No normal-speed audiovisual/AAA approval.',
                        'whiff_baseline':list(baseline),'whiff_after':[after['impact']['count'],after['impact']['spawn_count']],
                        'contact_snapshot':contact,'contact_events':charged_events,'physical_sample_checks':checks,
                        'frozen_contact_check':frozen_contact,
                        'resolved_recoil_horizontal_m':recoil,'final':final,'touch_observation':observation})
                    qa.mark('charged_heavy_completed')
                    qa.write('charged-heavy-result.json',{'outcome':'charged_heavy_focused_passed','seconds':round(time.monotonic()-qa.started,3),'errors':qa.errors,
                        'scope':'Actual charged whiff/no burst, first encounter charged contact, once per strike-target,69.3 damage/heavy_hit/.075 both-hitstop/collision recoil only; not full workflow or AAA audiovisual approval'})
                except Exception:
                    await save_contact_timeline(qa)
                    await qa.failure();raise
                finally:
                    await context.close();context=None
    except Exception as error:
        qa.write('charged-heavy-result.json',{'outcome':'failed','stage':qa.stage,'seconds':round(time.monotonic()-qa.started,3),
            'errors':qa.errors,'exception_type':type(error).__name__,'exception':str(error)})
        raise
    finally:
        qa.write('charged-heavy-errors.json',qa.errors)
        qa.write('charged-heavy-dispatched-inputs.json',qa.events)
        if context:await context.close()
