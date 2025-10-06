
// Objetivo, tener un temporizador de 1 hora para el usuario
// Donde inicia cuando este empiece la prueba
// y sea independiente a lo que haga el alumno, 

// static/js/diagnostico/timer.js
import { parseISO } from './utils.js';

export class CountdownTimer {
  constructor({serverNowIso, endTimeIso, onTick=null, onFinish=null}){
    this.serverNow = parseISO(serverNowIso);
    this.endTime = parseISO(endTimeIso);
    this.onTick = onTick;
    this.onFinish = onFinish;
    this.interval = null;

    // compute client-server skew: clientNow - serverNow
    this.clientNow = new Date();
    this.skewMs = this.clientNow - this.serverNow;
  }

  _remainingSeconds(){
    const clientNow = new Date();
    const approximatedServerNow = new Date(clientNow - this.skewMs);
    const diffMs = this.endTime - approximatedServerNow;
    return Math.max(0, Math.floor(diffMs / 1000));
  }

  start(){
    // corre altiro cada 1 ss
    if (this.interval) clearInterval(this.interval);
    this._tick();
    this.interval = setInterval(()=> this._tick(), 1000);
  }

  _tick(){
    const remaining = this._remainingSeconds();
    if (this.onTick) this.onTick(remaining);
    if (remaining <= 0) {
      this.stop();
      if (this.onFinish) this.onFinish();
    }
  }

  stop(){
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }
}









// export class Timer{
//     constructor(endTimestamp, offset = 0){ //corregir la hora local frente a la hora "servidor"
//         this.endTimestamp = endTimestamp;
//         this.offset = offset;
//         this.intervalId = null;
//     }
//     getRemainingMs(){ //calcula el tiempo restante en cada tick basandose en la hora actual Date.now() (evita decrementar un contador)
//         return this.endTimestamp - (Date.now() + this.offset);
//     }
//     // llama a callbackTick(remMs) cada segundo con los ms restantes a callbackEnd() cuando se agota

//     start(callbackTick, callbackEnd){
//         if(this.intervalId) clearInterval(this.intervalId);
//         const tickFn = ()=>{
//             const rem = this.getRemainingMs();
//             if (rem<=0){
//                 clearInterval(this.intervalId);
//                 callbackEnd()
//             } else{
//                 callbackTick(rem)
//             }
//         };
//         tickFn();
//         this.intervalId = setInterval(tickFn,1000);
//     }
//     stop(){
//        if (this.intervalId) clearInterval(this.intervalId) 
//     }

// }

