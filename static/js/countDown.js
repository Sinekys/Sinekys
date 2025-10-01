// Cuenta regresiva 
// 1 hora para la prueba de diagnóstico
export default function() {
    const $countdown = document.getElementById(id),//variable del dom 
    countdownDate = new Date(limitDate).getTime();
    let countdownTempo = setInterval(()=>{
        let now = new Date().getTime(),
        limitTime = countdownDate - now,
        minutes = (45*60*1000), //2700000
        seconds = (60*1000);
    }, 1000)


    $countdown.innerHTML = `<p>Tiempo: ${minutes}:${seconds}</p>` 

}