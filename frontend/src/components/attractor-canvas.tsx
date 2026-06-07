// @ts-nocheck
"use client";
import { useEffect, useRef } from "react";
import { useThemeStore } from "@/store/theme";

/* ── RK4 for 3D systems ─────────────────────────────────────────── */
type Vec3 = [number, number, number];

function rk4(s: Vec3, dt: number, f: (s: Vec3) => Vec3): Vec3 {
  const k1 = f(s);
  const k2 = f([s[0]+dt/2*k1[0], s[1]+dt/2*k1[1], s[2]+dt/2*k1[2]]);
  const k3 = f([s[0]+dt/2*k2[0], s[1]+dt/2*k2[1], s[2]+dt/2*k2[2]]);
  const k4 = f([s[0]+dt*k3[0],   s[1]+dt*k3[1],   s[2]+dt*k3[2]]);
  return [
    s[0]+dt/6*(k1[0]+2*k2[0]+2*k3[0]+k4[0]),
    s[1]+dt/6*(k1[1]+2*k2[1]+2*k3[1]+k4[1]),
    s[2]+dt/6*(k1[2]+2*k2[2]+2*k3[2]+k4[2]),
  ];
}

function rossler([x,y,z]: Vec3): Vec3 { return [-y-z, x+0.2*y, 0.2+z*(x-5.7)]; }
function thomas([x,y,z]: Vec3): Vec3 {
  const b=0.19832;
  return [Math.sin(y)-b*x, Math.sin(z)-b*y, Math.sin(x)-b*z];
}

function project3D(x:number,y:number,z:number,rx:number,ry:number,cx:number,cy:number,sc:number):[number,number] {
  const x1=x*Math.cos(ry)+z*Math.sin(ry), z1=-x*Math.sin(ry)+z*Math.cos(ry);
  const y2=y*Math.cos(rx)-z1*Math.sin(rx), z2=y*Math.sin(rx)+z1*Math.cos(rx);
  return [cx+x1*sc*(1+z2*0.004), cy+y2*sc*(1+z2*0.004)];
}

/* ── Three-body ─────────────────────────────────────────────────── */
interface Body { x:number;y:number;vx:number;vy:number;mass:number;trail:[number,number][];h:number; }

const SOFTEN=0.06, G_TB=1.0, TB_TRAIL=1000, ESCAPE_R=7;

function randomBodies(): Body[] {
  const hues=[265,340,130];
  const bs: Body[] = hues.map(h=>({
    x:(Math.random()-0.5)*2.8, y:(Math.random()-0.5)*1.8,
    vx:(Math.random()-0.5)*0.9, vy:(Math.random()-0.5)*0.9,
    mass:0.7+Math.random()*0.7, trail:[], h,
  }));
  const M=bs.reduce((s,b)=>s+b.mass,0);
  const cmvx=bs.reduce((s,b)=>s+b.mass*b.vx,0)/M, cmvy=bs.reduce((s,b)=>s+b.mass*b.vy,0)/M;
  const cmx =bs.reduce((s,b)=>s+b.mass*b.x, 0)/M, cmy =bs.reduce((s,b)=>s+b.mass*b.y, 0)/M;
  bs.forEach(b=>{b.vx-=cmvx;b.vy-=cmvy;b.x-=cmx;b.y-=cmy;});
  return bs;
}

function stepBodies(bs: Body[], dt: number) {
  const acc=bs.map((bi,i)=>{
    let ax=0,ay=0;
    bs.forEach((bj,j)=>{ if(i===j) return;
      const dx=bj.x-bi.x, dy=bj.y-bi.y;
      const r3=(dx*dx+dy*dy+SOFTEN*SOFTEN)**1.5;
      ax+=G_TB*bj.mass*dx/r3; ay+=G_TB*bj.mass*dy/r3;
    });
    return {ax,ay};
  });
  bs.forEach((b,i)=>{
    b.vx+=acc[i].ax*dt; b.vy+=acc[i].ay*dt;
    b.x+=b.vx*dt;       b.y+=b.vy*dt;
    if(b.trail.length>=TB_TRAIL) b.trail.shift();
    b.trail.push([b.x,b.y]);
  });
}

/* ── Component ──────────────────────────────────────────────────── */
export function AttractorCanvas() {
  const dark = useThemeStore((s) => s.dark);
  const darkRef = useRef(dark);
  useEffect(() => { darkRef.current = dark; }, [dark]);

  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(()=>{
    const canvas=ref.current; if(!canvas) return;
    const ctx=canvas.getContext("2d"); if(!ctx) return;

    /* init attractors */
    let rs: Vec3=[1,0,0];
    const rTrail: Vec3[]=[];
    for(let i=0;i<2000;i++) rs=rk4(rs,0.015,rossler);

    let ts: Vec3=[0.1,0,-0.1];
    const tTrail: Vec3[]=[];
    for(let i=0;i<500;i++) ts=rk4(ts,0.05,thomas);

    let bodies=randomBodies();
    let resetFlash=0, restartIn=0, tbAge=0;
    const MIN_AGE=300;

    let rx=0.28, ry=0;

    function resize(){
      const dpr=window.devicePixelRatio||1;
      canvas.width=canvas.offsetWidth*dpr;
      canvas.height=canvas.offsetHeight*dpr;
    }
    resize();
    const ro=new ResizeObserver(resize); ro.observe(canvas);

    let raf=0;

    function draw(t: number){
      const isDark=darkRef.current;
      const w=canvas.width, h=canvas.height;
      const cx=w*0.5, cy=h*0.5;
      const scR=Math.min(w,h)*0.044;
      const scT=Math.min(w,h)*0.11;
      const scTB=Math.min(w,h)*0.085;
      const tbCx=w*0.44, tbCy=h*0.52;

      /* advance Rössler */
      for(let i=0;i<4;i++){
        rs=rk4(rs,0.015,rossler);
        if(rTrail.length>=3000) rTrail.shift();
        rTrail.push([...rs]);
      }
      /* advance Thomas */
      for(let i=0;i<2;i++){
        ts=rk4(ts,0.05,thomas);
        if(tTrail.length>=2000) tTrail.shift();
        tTrail.push([...ts]);
      }
      /* advance 3-body */
      tbAge++;
      if(restartIn>0){
        restartIn--;
        if(restartIn===0){ bodies=randomBodies(); resetFlash=1; tbAge=0; }
      } else {
        for(let i=0;i<3;i++) stepBodies(bodies,0.012);
        if(tbAge>MIN_AGE && bodies.some(b=>Math.hypot(b.x,b.y)>ESCAPE_R)) restartIn=90;
      }

      ry+=0.00032;
      rx=0.28+Math.sin(t*0.00007)*0.13;

      /* ── clear with fade — color depends on theme ─────────────── */
      ctx.fillStyle = isDark
        ? "rgba(5,10,22,0.20)"          // dark navy fade
        : "rgba(253,250,242,0.22)";     // warm cream fade
      ctx.fillRect(0,0,w,h);

      /* ── Rössler — teal (bright on dark, deep on light) ───────── */
      for(let i=1;i<rTrail.length;i++){
        const f=i/rTrail.length;
        const [x0,y0,z0]=rTrail[i-1]; const [x1,y1,z1]=rTrail[i];
        const [px0,py0]=project3D(x0,y0,z0,rx,ry,cx,cy*0.82,scR);
        const [px1,py1]=project3D(x1,y1,z1,rx,ry,cx,cy*0.82,scR);
        const hue=165+(z1+3)*3;
        const lum=isDark ? 35+f*35 : 22+f*22;
        const alpha=isDark ? f*0.62 : f*0.70;
        ctx.beginPath();
        ctx.strokeStyle=`hsla(${hue},88%,${lum}%,${alpha})`;
        ctx.lineWidth=0.7+f*0.7;
        ctx.moveTo(px0,py0); ctx.lineTo(px1,py1); ctx.stroke();
      }
      { const [px,py]=project3D(rs[0],rs[1],rs[2],rx,ry,cx,cy*0.82,scR);
        const g=ctx.createRadialGradient(px,py,0,px,py,6);
        const c=isDark?"rgba(45,212,191,0.95)":"rgba(13,148,136,0.95)";
        g.addColorStop(0,c); g.addColorStop(1,"rgba(45,212,191,0)");
        ctx.fillStyle=g; ctx.beginPath(); ctx.arc(px,py,6,0,Math.PI*2); ctx.fill(); }

      /* ── Thomas — amber (bright on dark, deep on light) ──────── */
      for(let i=1;i<tTrail.length;i++){
        const f=i/tTrail.length;
        const [x0,y0,z0]=tTrail[i-1]; const [x1,y1,z1]=tTrail[i];
        const [px0,py0]=project3D(x0,y0,z0,rx+0.35,ry+0.6,cx,cy*0.82,scT);
        const [px1,py1]=project3D(x1,y1,z1,rx+0.35,ry+0.6,cx,cy*0.82,scT);
        const hue=28+(z1+1)*10;
        const lum=isDark ? 30+f*30 : 20+f*25;
        const alpha=isDark ? f*0.42 : f*0.55;
        ctx.beginPath();
        ctx.strokeStyle=`hsla(${hue},90%,${lum}%,${alpha})`;
        ctx.lineWidth=0.6+f*0.5;
        ctx.moveTo(px0,py0); ctx.lineTo(px1,py1); ctx.stroke();
      }
      { const [px,py]=project3D(ts[0],ts[1],ts[2],rx+0.35,ry+0.6,cx,cy*0.82,scT);
        const g=ctx.createRadialGradient(px,py,0,px,py,5);
        const c=isDark?"rgba(251,146,60,0.90)":"rgba(180,83,9,0.90)";
        g.addColorStop(0,c); g.addColorStop(1,"rgba(251,146,60,0)");
        ctx.fillStyle=g; ctx.beginPath(); ctx.arc(px,py,5,0,Math.PI*2); ctx.fill(); }

      /* ── Three-body — violet/rose/green ──────────────────────── */
      const tbAlpha=restartIn>0 ? Math.max(0,restartIn/90) : 1;
      bodies.forEach(body=>{
        const tlen=body.trail.length;
        for(let i=1;i<tlen;i++){
          const f=i/tlen;
          const [x0,y0]=body.trail[i-1]; const [x1,y1]=body.trail[i];
          const lum=isDark ? 45+f*30 : 28+f*25;
          const alpha=isDark ? f*0.55*tbAlpha : f*0.65*tbAlpha;
          ctx.beginPath();
          ctx.strokeStyle=`hsla(${body.h},80%,${lum}%,${alpha})`;
          ctx.lineWidth=0.65+f*0.65;
          ctx.moveTo(tbCx+x0*scTB, tbCy+y0*scTB);
          ctx.lineTo(tbCx+x1*scTB, tbCy+y1*scTB); ctx.stroke();
        }
        if(body.trail.length>0){
          const [lx,ly]=body.trail[body.trail.length-1];
          const px=tbCx+lx*scTB, py=tbCy+ly*scTB;
          const g=ctx.createRadialGradient(px,py,0,px,py,7);
          const lum=isDark?75:45;
          g.addColorStop(0,`hsla(${body.h},90%,${lum}%,${0.95*tbAlpha})`);
          g.addColorStop(1,`hsla(${body.h},90%,${lum}%,0)`);
          ctx.fillStyle=g; ctx.beginPath(); ctx.arc(px,py,7,0,Math.PI*2); ctx.fill();
        }
      });

      /* ── restart pulse ──────────────────────────────────────── */
      if(resetFlash>0){
        ctx.fillStyle=`rgba(139,92,246,${resetFlash*0.15})`;
        ctx.fillRect(0,0,w,h);
        resetFlash=Math.max(0,resetFlash-0.025);
      }

      raf=requestAnimationFrame(draw);
    }

    raf=requestAnimationFrame(draw);
    return ()=>{ cancelAnimationFrame(raf); ro.disconnect(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);

  return (
    <canvas ref={ref} className="absolute inset-0 w-full h-full" style={{ opacity: 0.92 }} />
  );
}
