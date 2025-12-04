export function pad2(n){ return n.toString().padStart(2,'0'); }

export function formatSeconds(sec){
  if (sec < 0) sec = 0;
  const minutes = Math.floor(sec / 60);
  const seconds = sec % 60;
  return `${pad2(minutes)}:${pad2(seconds)}`;
}

export function parseISO(iso){ 
  return new Date(iso);
}
