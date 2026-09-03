import asyncio
import logging
import time

from comandos.ECONOMIA.GLOBAL.orquestrador import OrquestradorEconomiaGlobal


class CicloAutomaticoEconomia:
    """Executa a economia global em segundo plano sem bloquear o bot."""

    def __init__(self, bot, db, intervalo_segundos=300):
        self.bot = bot
        self.db = db
        self.intervalo_segundos = max(60, int(intervalo_segundos))
        self._task = None
        self._ativo = False
        self._motor = None
        self._executando = False
        self.ultima_execucao = None
        self.ultima_duracao = 0.0

    async def iniciar(self):
        if self._ativo:
            return
        self._ativo = True
        self._task = asyncio.create_task(self._loop(), name="ciclo_economia_global")

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

        # Evita competir com o carregamento inicial e com os primeiros comandos.
        await asyncio.sleep(self.intervalo_segundos)

        while self._ativo and not self.bot.is_closed():
            inicio = time.perf_counter()
            try:
                await self.executar_uma_vez()
            except Exception:
                logging.exception("Erro no ciclo automático da economia")
            finally:
                self.ultima_execucao = time.time()
                self.ultima_duracao = time.perf_counter() - inicio

            await asyncio.sleep(self.intervalo_segundos)

    async def executar_uma_vez(self):
        if self._executando:
            logging.warning("Ciclo econômico ignorado: uma execução anterior ainda está ativa.")
            return None

        self._executando = True
        try:
            if self._motor is None:
                from comandos.ECONOMIA.GLOBAL.motor import MotorEconomiaGlobal
                self._motor = MotorEconomiaGlobal(self.db)

            orquestrador = OrquestradorEconomiaGlobal(self._motor)
            return await asyncio.to_thread(orquestrador.executar_ciclo_completo)
        finally:
            self._executando = False


def configurar_ciclo_economico(bot, db, intervalo_segundos=300):
    """Cria ou reutiliza o controlador do ciclo econômico global."""
    existente = getattr(bot, "ciclo_economia_global", None)
    if existente is not None:
        return existente

    ciclo = CicloAutomaticoEconomia(bot, db, intervalo_segundos)
    bot.ciclo_economia_global = ciclo
    return ciclo
