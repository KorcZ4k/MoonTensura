import asyncio
import logging

from comandos.ECONOMIA.GLOBAL.orquestrador import OrquestradorEconomiaGlobal


class CicloAutomaticoEconomia:
    """Executa a economia global em intervalos fixos sem bloquear o bot."""

    def __init__(self, bot, db, intervalo_segundos=60):
        self.bot = bot
        self.db = db
        self.intervalo_segundos = max(30, int(intervalo_segundos))
        self._task = None
        self._ativo = False
        self._motor = None

    async def iniciar(self):
        if self._ativo:
            return
        self._ativo = True
        self._task = asyncio.create_task(self._loop())

    async def parar(self):
        self._ativo = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        await self.bot.wait_until_ready()
        while self._ativo and not self.bot.is_closed():
            try:
                await self.executar_uma_vez()
            except Exception:
                logging.exception("Erro no ciclo automático da economia")
            await asyncio.sleep(self.intervalo_segundos)

    async def executar_uma_vez(self):
        if self._motor is None:
            from comandos.ECONOMIA.GLOBAL.motor import MotorEconomiaGlobal
            self._motor = MotorEconomiaGlobal(self.db)

        orquestrador = OrquestradorEconomiaGlobal(self._motor)
        return await asyncio.to_thread(orquestrador.executar_ciclo_completo)


def configurar_ciclo_economico(bot, db, intervalo_segundos=60):
    """Cria ou reutiliza o controlador do ciclo econômico global."""
    existente = getattr(bot, "ciclo_economia_global", None)
    if existente is not None:
        return existente
    ciclo = CicloAutomaticoEconomia(bot, db, intervalo_segundos)
    bot.ciclo_economia_global = ciclo
    return ciclo
