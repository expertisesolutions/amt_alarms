"""The Intelbras AMT Alarms integration."""
import asyncio
import socket
import time
from typing import Union

import crcengine
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)

from .const import (
    AMT_COMMAND_CODE_CONECTAR,
    AMT_COMMAND_CODE_EVENT_CONTACT_ID,
    AMT_COMMAND_CODE_EVENT_DATA_HORA,
    AMT_COMMAND_CODE_HEARTBEAT,
    AMT_COMMAND_CODE_SOLICITA_DATA_HORA,
    AMT_EVENT_CODE_ATIVACAO_PARCIAL,
    AMT_EVENT_CODE_ATIVACAO_PELO_USUARIO,
    AMT_EVENT_CODE_ATIVACAO_POR_UMA_TECLA,
    AMT_EVENT_CODE_ATIVACAO_VIA_COMPUTADOR_OU_TELEFONE,
    AMT_EVENT_CODE_AUTO_ATIVACAO,
    AMT_EVENT_CODE_AUTO_DESATIVACAO,
    AMT_EVENT_CODE_CORTE_DA_FIACAO_DOS_SENSORES,
    AMT_EVENT_CODE_CORTE_OU_CURTO_CIRCUITO_NA_SIRENE,
    AMT_EVENT_CODE_CURTO_CIRCUITO_NA_FIACAO_DOS_SENSORES,
    AMT_EVENT_CODE_DESATIVACAO_PELO_USUARIO,
    AMT_EVENT_CODE_DESATIVACAO_VIA_COMPUTADOR_OU_TELEFONE,
    AMT_EVENT_CODE_DISPARO_DE_CERCA_ELETRICA,
    AMT_EVENT_CODE_DISPARO_DE_ZONA,
    AMT_EVENT_CODE_DISPARO_DE_ZONA_24H,
    AMT_EVENT_CODE_DISPARO_OU_PANICO_DE_INCENDIO,
    AMT_EVENT_CODE_DISPARO_SILENCIOSO,
    AMT_EVENT_CODE_EMERGENCIA_MEDICA,
    AMT_EVENT_CODE_FALHA_AO_COMUNICAR_EVENTO,
    AMT_EVENT_CODE_FALHA_NA_LINHA_TELEFONICA,
    AMT_EVENT_CODE_PANICO_AUDIVEL_OU_SILENCIOSO,
    AMT_EVENT_CODE_PANICO_SILENCIOSO,
    AMT_EVENT_CODE_PROBLEMA_EM_TECLADO_OU_RECEPTOR,
    AMT_EVENT_CODE_RESTARAUCAO_BAT_PRINC_AUSENTE_OU_INVERTIDA,
    AMT_EVENT_CODE_RESTARAUCAO_BAT_PRINC_BAIXA_OU_EM_CURTO_CIRCUITO,
    AMT_EVENT_CODE_RESTARAUCAO_BATERIA_BAIXA_DE_SENSOR_SEM_FIO,
    AMT_EVENT_CODE_RESTARAUCAO_CORTE_DA_FIACAO_DOS_SENSORES,
    AMT_EVENT_CODE_RESTARAUCAO_CORTE_OU_CURTO_CIRCUITO_NA_SIRENE,
    AMT_EVENT_CODE_RESTARAUCAO_CURTO_CIRCUITO_NA_FIACAO_DOS_SENSORES,
    AMT_EVENT_CODE_RESTARAUCAO_DA_SUPERVISAO_SMART,
    AMT_EVENT_CODE_RESTARAUCAO_DISPARO_DE_ZONA_24H,
    AMT_EVENT_CODE_RESTARAUCAO_DISPARO_SILENCIOSO,
    AMT_EVENT_CODE_RESTARAUCAO_FALHA_NA_REDE_ELETRICA,
    AMT_EVENT_CODE_RESTARAUCAO_LINHA_TELEFONICA,
    AMT_EVENT_CODE_RESTARAUCAO_PROBLEMA_EM_TECLADO_OU_RECEPTOR,
    AMT_EVENT_CODE_RESTARAUCAO_SOBRECARGA_NA_SAIDA_AUXILIAR,
    AMT_EVENT_CODE_RESTARAUCAO_TAMPER_DO_SENSOR,
    AMT_EVENT_CODE_RESTARAUCAO_TAMPER_DO_TECLADO,
    AMT_EVENT_CODE_RESTAURACAO_DE_DISPARO_DE_CERCA_ELETRICA,
    AMT_EVENT_CODE_RESTAURACAO_DE_INCENDIO,
    AMT_EVENT_CODE_RESTAURACAO_DISPARO_DE_ZONA,
    AMT_EVENT_CODE_SENHA_DE_COACAO,
    AMT_EVENT_CODE_TAMPER_DO_SENSOR,
    AMT_EVENT_CODE_TAMPER_DO_TECLADO,
    AMT_EVENT_MESSAGES,
    AMT_PROTOCOL_ISEC_MOBILE,
    AMT_REQ_CODE_MAC,
    CONF_AWAY_MODE_ENABLED,
    CONF_AWAY_PARTITION_1,
    CONF_AWAY_PARTITION_2,
    CONF_AWAY_PARTITION_3,
    CONF_AWAY_PARTITION_4,
    CONF_AWAY_PARTITION_LIST,
    CONF_HOME_MODE_ENABLED,
    CONF_HOME_PARTITION_1,
    CONF_HOME_PARTITION_2,
    CONF_HOME_PARTITION_3,
    CONF_HOME_PARTITION_4,
    CONF_HOME_PARTITION_LIST,
    CONF_NIGHT_PARTITION_1,
    CONF_NIGHT_PARTITION_2,
    CONF_NIGHT_PARTITION_3,
    CONF_NIGHT_PARTITION_4,
    CONF_NIGHT_PARTITION_LIST,
    CONF_PASSWORD,
    CONF_PORT,
    DOMAIN,
    LOGGER,
)

# import traceback


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PORT): cv.port,
                vol.Optional(CONF_PASSWORD): int,
                vol.Optional(CONF_NIGHT_PARTITION_1): bool,
                vol.Optional(CONF_NIGHT_PARTITION_2): bool,
                vol.Optional(CONF_NIGHT_PARTITION_3): bool,
                vol.Optional(CONF_NIGHT_PARTITION_4): bool,
                vol.Optional(CONF_AWAY_MODE_ENABLED): bool,
                vol.Optional(CONF_AWAY_PARTITION_1): bool,
                vol.Optional(CONF_AWAY_PARTITION_2): bool,
                vol.Optional(CONF_AWAY_PARTITION_3): bool,
                vol.Optional(CONF_AWAY_PARTITION_4): bool,
                vol.Optional(CONF_HOME_MODE_ENABLED): bool,
                vol.Optional(CONF_HOME_PARTITION_1): bool,
                vol.Optional(CONF_HOME_PARTITION_2): bool,
                vol.Optional(CONF_HOME_PARTITION_3): bool,
                vol.Optional(CONF_HOME_PARTITION_4): bool,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    print("async_unload_entry")
    LOGGER.error("async_unload_entry")
    # unload_ok = all(
    #     await asyncio.gather(
    #         *[
    #             hass.config_entries.async_forward_entry_unload(entry, component)
    #             for component in PLATFORMS
    #         ]
    #     )
    # )
    # if unload_ok:
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _bcd_to_decimal(mbytes: bytes, unescape_zeros=True):
    """Convert a sequence of bcd encoded decimal to integer."""

    def unescape_zero(i: int):
        return i if i != 0xA else 0

    if unescape_zeros:
        mbytes = bytes(unescape_zero(b) for b in mbytes)

    len_mbytes = len(mbytes)
    return sum(10 ** (len_mbytes - i - 1) * b for i, b in enumerate(mbytes))


def _decimal_to_bcd_nibble(decimal: int):
    """Convert a decimal between 0 to 99 into two bcd encoded nibbles."""
    if decimal < 0 or decimal > 99:
        raise ValueError("argument must be non negative")

    ones = decimal % 10
    tens = decimal // 10

    return tens << 4 | ones


class AlarmHub:
    """Placeholder class to make tests pass."""

    def __init__(
        self, hass: HomeAssistant, config_entry: ConfigEntry, port, password=None
    ) -> None:
        """Initialize."""
        LOGGER.error("AlarmHub instantiation")
        print("AlarmHub instantiation")
        if password is not None:
            self.password = str(password)
            if len(self.password) != 4 and len(self.password) != 6:
                raise ValueError

        self.hass = hass
        self.config_entry = config_entry
        self.port = port
        self._timeout = 10.0

        self.polling_task = None
        self.reading_task = None
        self.update_event = asyncio.Event()

        self.socket: Union[None, socket.socket] = None
        self.client_socket: Union[None, socket.socket] = None
        self.writer: asyncio.StreamWriter = None
        self.reader: asyncio.StreamReader = None
        self.is_initialized = False
        self.crc = crcengine.create(0xAB, 8, 0, False, False, "", 0)
        self.disarm_crc = crcengine.create(0xAB, 8, 0, False, False, "", 0xFF)
        self.recv_crc = crcengine.create(0x01, 8, 0xFF, False, False, "", 0)
        # self.disarm_crc = crcengine.create(0xBA, 8, 0, False, False, "", 0xFF)
        # self.disarm_crc = self.crc

        self.open_sensors: list[Union[None, bool]] = [None] * self.max_sensors
        self.partitions: list[Union[None, bool]] = [None] * self.max_partitions
        self.triggered_partitions = [False] * self.max_partitions
        self.triggered_sensors = [False] * self.max_sensors
        # self.open_sensors[0:47] = False

        # self.t2 = 0

        self.listeners: list[AlarmControlPanelEntity] = []
        self._mac_address = bytes([])
        self.outstanding_buffer = bytes([])
        self._read_timestamp = 0.0
        self.read_task = None

    @property
    def name(self):
        """Return unique name from device."""
        return "AMTAlarm"

    async def send_request_zones(self):
        """Send Request Information packet."""
        if self.password is None:
            raise ValueError

        buf = bytes([])
        buf = buf + b"\x0a\xe9\x21"

        buf = buf + self.password.encode("utf-8")

        if len(self.password) == 4:
            buf = buf + b"00"

        buf = buf + b"\x5b\x21\x00"
        crc = self.crc(buf)
        buf = buf[0 : len(buf) - 1] + bytes([crc])

        try:
            self.writer.write(buf)
            await self.writer.drain()
        except OSError as e:
            self.polling_task = None
            LOGGER.error("Connection error: %s", e)
            await self.__accept_new_connection()
        except Exception as e:
            self.polling_task = None
            LOGGER.error("Some unknown error: %s", e)
            await self.__accept_new_connection()
            raise

    async def send_arm_partition(self, partition: int):
        """Send Request Information packet."""

        # print("arm partition", partition+1, file=sys.stderr)

        if self.password is None:
            raise ValueError

        buf = bytes([])
        buf = buf + b"\x0b\xe9\x21"

        buf = buf + self.password.encode("utf-8")

        if len(self.password) == 4:
            buf = buf + b"00"

        buf = buf + b"\x41"
        buf = buf + bytes([0x40 + partition + 1])
        buf = buf + b"\x21\x00"
        crc = self.crc(buf)
        buf = buf[0 : len(buf) - 1] + bytes([crc])
        # print("arm partition req buf ", buf, file=sys.stderr)

        try:
            self.writer.write(buf)
            await self.writer.drain()
        except OSError as e:
            self.polling_task = None
            LOGGER.error("Connection error %s", e)
            await self.__accept_new_connection()
        except Exception as e:
            self.polling_task = None
            LOGGER.error("Some unknown error %s", e)
            await self.__accept_new_connection()
            raise

    async def send_disarm_partition(self, partition: int):
        """Send Request Information packet."""

        # print("arm partition", partition+1, file=sys.stderr)

        if self.password is None:
            raise ValueError

        buf = bytes([])
        buf = buf + b"\x0b\xe9\x21"

        buf = buf + self.password.encode("utf-8")

        if len(self.password) == 4:
            buf = buf + b"00"

        buf = buf + b"\x44"
        buf = buf + bytes([0x40 + partition + 1])
        buf = buf + b"\x21\x00"
        crc = self.disarm_crc(buf)
        buf = buf[0 : len(buf) - 1] + bytes([crc])
        # print("disarm partition req buf ", buf, file=sys.stderr)

        try:
            self.writer.write(buf)
            await self.writer.drain()
        except OSError as e:
            self.polling_task = None
            LOGGER.error("Connection error %s", e)
            await self.__accept_new_connection()
        except Exception as e:
            self.polling_task = None
            LOGGER.error("Some unknown error %s", e)
            await self.__accept_new_connection()
            raise

    async def send_test(self):
        """Send Reverse Engineering Test."""

        # unsigned char buffer[] = {0x0b, 0xe9, 0x21, /* senha */ 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, /* fim da senha */ 0x41, 0x40 + partition, 0x21, 0x00};
        # self.t1 = 0x44

        # while True: #if True: if self.password is None: raise
        # ValueError

        #     print("send test") buf = bytes([], file=sys.stderr) #buf = buf +
        #     b"\x0b\xe9" + bytes([0x21]) buf = buf + b"\x0a\xe9" +
        #     bytes([0x21])

        #     buf = buf + self.password.encode("utf-8") if
        #     len(self.password) == 4: buf = buf + b"00"

        #     buf = buf + bytes([self.t1]) #buf = buf + bytes([0x40 + 3+
        #     1]) buf = buf + bytes([0x21]) + b"\x00" self.t1 += 1

        #     crc = self.crc(buf) buf = buf[0 : len(buf) - 1] +
        #     bytes([crc]) print("buf length ", len(buf), file=sys.stderr) print("req buf
        #     ", buf)

        #     self.writer.write(buf) await self.writer.drain() await
        #     asyncio.sleep(1)

        #     print("wrote", file=sys.stderr)

    async def __send_ack(self):
        try:
            self.writer.write(bytes([0xFE]))
            await self.writer.drain()
        except OSError as e:
            self.polling_task = None
            LOGGER.error("Connection error %s", e)
            await self.__accept_new_connection()
        except Exception as e:
            self.polling_task = None
            LOGGER.error("Some unknown error %s", e)
            await self.__accept_new_connection()
            raise

    async def send_message(self, packet: bytes):
        """Send packet."""
        try:
            self.writer.write(packet)
            await self.writer.drain()
        except OSError as e:
            self.polling_task = None
            LOGGER.error("Connection error %s", e)
            await self.__accept_new_connection()
        except Exception as e:
            self.polling_task = None
            LOGGER.error("Some unknown error %s", e)
            await self.__accept_new_connection()
            raise

    def __handle_amt_event(self, event: int, partition: int, zone: int, client_id):
        if event in (
            AMT_EVENT_CODE_DESATIVACAO_PELO_USUARIO,
            AMT_EVENT_CODE_AUTO_DESATIVACAO,
            AMT_EVENT_CODE_DESATIVACAO_VIA_COMPUTADOR_OU_TELEFONE,
        ):
            # print(
            #     "deactivated, will untrigger too if there is any trigger partition",
            #     partition,
            #     file=sys.stderr,
            # )
            # print("state before", self.partitions)
            if partition == -1:
                self.partitions = [False] * self.max_partitions
                self.triggered_partitions = [False] * self.max_partitions
                self.triggered_sensors = [False] * self.max_sensors
            else:
                self.partitions[partition] = False
                self.triggered_partitions = [False] * self.max_partitions
                self.triggered_sensors = [False] * self.max_sensors
            # print("state after", self.partitions)
        elif event in (
            AMT_EVENT_CODE_ATIVACAO_PELO_USUARIO,
            AMT_EVENT_CODE_AUTO_ATIVACAO,
            AMT_EVENT_CODE_ATIVACAO_VIA_COMPUTADOR_OU_TELEFONE,
            AMT_EVENT_CODE_ATIVACAO_POR_UMA_TECLA,
            AMT_EVENT_CODE_ATIVACAO_PARCIAL,
        ):
            # print("Activated partition (untriggering too)", partition, file=sys.stderr)
            if partition != -1 and zone != -1 and zone < self.max_sensors:
                self.triggered_sensors[zone] = False
            if partition == -1:
                self.triggered_partitions = [False] * self.max_partitions
            else:
                self.triggered_partitions[partition] = False

            # print("state before", self.partitions)
            if partition == -1:
                self.partitions = [True] * self.max_partitions
            else:
                self.partitions[partition] = True
            # print("state after", self.partitions)
        if event == AMT_EVENT_CODE_FALHA_AO_COMUNICAR_EVENTO:
            LOGGER.error("Alarm panel error: %s", AMT_EVENT_MESSAGES[event])
        if event in (
            AMT_EVENT_CODE_EMERGENCIA_MEDICA,
            AMT_EVENT_CODE_DISPARO_OU_PANICO_DE_INCENDIO,
            AMT_EVENT_CODE_PANICO_AUDIVEL_OU_SILENCIOSO,
            AMT_EVENT_CODE_SENHA_DE_COACAO,
            AMT_EVENT_CODE_PANICO_SILENCIOSO,
            AMT_EVENT_CODE_DISPARO_DE_ZONA,
            AMT_EVENT_CODE_DISPARO_DE_CERCA_ELETRICA,
            AMT_EVENT_CODE_DISPARO_DE_ZONA_24H,
            AMT_EVENT_CODE_TAMPER_DO_TECLADO,
            AMT_EVENT_CODE_DISPARO_SILENCIOSO,
            AMT_EVENT_CODE_CORTE_OU_CURTO_CIRCUITO_NA_SIRENE,
            AMT_EVENT_CODE_PROBLEMA_EM_TECLADO_OU_RECEPTOR,
            AMT_EVENT_CODE_FALHA_NA_LINHA_TELEFONICA,
            AMT_EVENT_CODE_CORTE_DA_FIACAO_DOS_SENSORES,
            AMT_EVENT_CODE_CURTO_CIRCUITO_NA_FIACAO_DOS_SENSORES,
            AMT_EVENT_CODE_TAMPER_DO_SENSOR,
        ):
            # print("Triggering partition ", partition, file=sys.stderr)
            LOGGER.error(
                "Triggering partition %d with error: %s",
                partition,
                AMT_EVENT_MESSAGES[event],
            )
            if partition != -1 and zone != -1 and zone < self.max_sensors:
                self.triggered_sensors[zone] = True
            if partition == -1:
                self.triggered_partitions = [True] * self.max_partitions
            else:
                self.triggered_partitions[partition] = True
        if event in (
            AMT_EVENT_CODE_RESTAURACAO_DE_INCENDIO,
            AMT_EVENT_CODE_RESTAURACAO_DISPARO_DE_ZONA,
            AMT_EVENT_CODE_RESTAURACAO_DE_DISPARO_DE_CERCA_ELETRICA,
            AMT_EVENT_CODE_RESTARAUCAO_DISPARO_DE_ZONA_24H,
            AMT_EVENT_CODE_RESTARAUCAO_TAMPER_DO_TECLADO,
            AMT_EVENT_CODE_RESTARAUCAO_DISPARO_SILENCIOSO,
            AMT_EVENT_CODE_RESTARAUCAO_DA_SUPERVISAO_SMART,
            AMT_EVENT_CODE_RESTARAUCAO_SOBRECARGA_NA_SAIDA_AUXILIAR,
            AMT_EVENT_CODE_RESTARAUCAO_FALHA_NA_REDE_ELETRICA,
            AMT_EVENT_CODE_RESTARAUCAO_BAT_PRINC_BAIXA_OU_EM_CURTO_CIRCUITO,
            AMT_EVENT_CODE_RESTARAUCAO_BAT_PRINC_AUSENTE_OU_INVERTIDA,
            AMT_EVENT_CODE_RESTARAUCAO_CORTE_OU_CURTO_CIRCUITO_NA_SIRENE,
            AMT_EVENT_CODE_RESTARAUCAO_PROBLEMA_EM_TECLADO_OU_RECEPTOR,
            AMT_EVENT_CODE_RESTARAUCAO_LINHA_TELEFONICA,
            AMT_EVENT_CODE_RESTARAUCAO_CORTE_DA_FIACAO_DOS_SENSORES,
            AMT_EVENT_CODE_RESTARAUCAO_CURTO_CIRCUITO_NA_FIACAO_DOS_SENSORES,
            AMT_EVENT_CODE_RESTARAUCAO_TAMPER_DO_SENSOR,
            AMT_EVENT_CODE_RESTARAUCAO_BATERIA_BAIXA_DE_SENSOR_SEM_FIO,
        ):
            # print("UN Triggering partition ", partition, file=sys.stderr)
            if partition != -1 and zone != -1 and zone < self.max_sensors:
                self.triggered_sensors[zone] = False
            if partition == -1:
                self.triggered_partitions = [False] * self.max_partitions
            else:
                self.triggered_partitions[partition] = False
        self.__call_listeners()

    async def __handle_packet(self, packet: bytes):
        cmd = packet[0]
        # print ('received packet cmd', cmd, file=sys.stderr)
        # if cmd == 0xF7 and len(packet) == 1:
        if cmd == AMT_COMMAND_CODE_HEARTBEAT and len(packet) == 1:
            # print("cmd 0xf7: ", packet, file=sys.stderr)
            await self.__send_ack()
        # elif cmd == 0x94:
        elif cmd == AMT_COMMAND_CODE_CONECTAR:
            # print("cmd 0x94: ", packet, file=sys.stderr)
            await self.__send_ack()
        # elif cmd == 0xC4:
        elif cmd == AMT_REQ_CODE_MAC and len(packet) == 7:
            # print("cmd 0xc4: ", packet, file=sys.stderr)
            self._mac_address = packet[1:7]
        # elif cmd == 0xB0 and len(packet) == 17 and packet[1] == 0x12:
        elif (
            cmd == AMT_COMMAND_CODE_EVENT_CONTACT_ID
            and len(packet) == 17
            and packet[1] == 0x12
        ):
            # print("cmd 0xb0: ", packet, file=sys.stderr)
            # def unescape_zero(i):
            #     return i if i != 0xA else 0

            # client_id = (
            #     unescape_zero(packet[2]) * 1000
            #     + unescape_zero(packet[3]) * 100
            #     + unescape_zero(packet[4]) * 10
            #     + unescape_zero(packet[5])
            # )
            client_id = _bcd_to_decimal(packet[2:6])
            # ev_id = (
            #     unescape_zero(packet[8]) * 1000
            #     + unescape_zero(packet[9]) * 100
            #     + unescape_zero(packet[10]) * 10
            #     + unescape_zero(packet[11])
            # )
            ev_id = _bcd_to_decimal(packet[8:12])
            # partition = unescape_zero(packet[12]) * 10 + unescape_zero(packet[13]) - 1
            partition = _bcd_to_decimal(packet[12:14]) - 1
            # zone = (
            #     unescape_zero(packet[14]) * 100
            #     + unescape_zero(packet[15]) * 10
            #     + unescape_zero(packet[16])
            # )
            zone = _bcd_to_decimal(packet[14:17])

            # print(
            #     "event",
            #     ev_id,
            #     "from partition",
            #     partition,
            #     "and zone",
            #     zone,
            #     "message:",
            #     AMT_EVENT_MESSAGES[ev_id],
            #     file=sys.stderr,
            # )
            self.__handle_amt_event(ev_id, partition, zone, client_id)

            await self.__send_ack()
        elif (
            cmd == AMT_COMMAND_CODE_EVENT_DATA_HORA
            and len(packet) == 29
            and packet[1] == 0x12
        ):
            pass
        elif cmd == AMT_COMMAND_CODE_SOLICITA_DATA_HORA:
            timezone = packet[1] if len(packet) > 1 else 0
            now = time.time()
            (
                tm_year,
                tm_mon,
                tm_mday,
                tm_hour,
                tm_min,
                tm_sec,
                tm_wday,
                _,
                _,
            ) = time.gmtime(now - timezone * 3600)
            tm_year -= 2000
            tm_wday = (tm_wday + 1) % 7 + 1

            response = bytes([cmd]) + bytes(
                map(
                    _decimal_to_bcd_nibble,
                    [tm_year, tm_mon, tm_mday, tm_wday, tm_hour, tm_min, tm_sec],
                )
            )
            await self.send_message(response)

        # elif (
        #     cmd == 0xE9
        #     and len(packet) == 2
        #     and (packet[1] == 0xE5 or packet[1] == 0xFE)
        # ):
        elif cmd == AMT_PROTOCOL_ISEC_MOBILE and len(packet) == 2:
            if packet[1] == 0xFE:
                await self.__send_ack()
            else:
                # print("cmd 0xe9: ", packet, file=sys.stderr)
                if packet[1] == 0xE1:
                    LOGGER.error("We are using wrong password in AMT integration?")
                elif packet[1] == 0xE2:
                    pass
                await self.__send_ack()
        # elif (
        #     cmd == AMT_PROTOCOL_ISEC_MOBILE
        #     and len(packet) == 2
        #     and packet[1] == 0xE1
        # ):
        #     print("cmd 0xe9: ", packet, file=sys.stderr)
        #     LOGGER.error("We are using wrong password in AMT integration?")
        #     await self.__send_ack()
        # elif cmd == 0xE9 and len(packet) >= 3 * 8:
        elif cmd == AMT_PROTOCOL_ISEC_MOBILE and len(packet) >= 3 * 8:
            # print("e9 update all partitions and zones", file=sys.stderr)
            for x in range(6):
                c = packet[x + 1]
                for i in range(8):
                    self.open_sensors[x * 8 + i] = ((c >> i) & 1) == 1

            c = packet[1 + 8 + 8 + 8 + 3]
            for i in range(2):
                self.partitions[i] = bool((c >> i) & 1)
                # if (c >> i) & 1:
                #     print("Partition ", i, " armed", file=sys.stderr)
            c = packet[1 + 8 + 8 + 8 + 3 + 1]
            for i in range(2):
                self.partitions[i + 2] = bool((c >> i) & 1)
                # if (c >> i) & 1:
                #     print("Partition ", i + 2, " armed", file=sys.stderr)

            self.is_initialized = True
            self.update_event.set()
            self.__call_listeners()
        else:
            LOGGER.warning("AMT doesn't know how to deal with %s ?", packet)

    async def __handle_data(self):
        while len(self.outstanding_buffer) != 0:
            is_nope = self.outstanding_buffer[0] == 0xF7
            packet_size = 1 if is_nope else self.outstanding_buffer[0]
            packet_start = 1 if not is_nope else 0

            if (
                not is_nope
                and len(self.outstanding_buffer) < packet_size + 1
                or self.outstanding_buffer[0] == 0
            ):
                break

            crc = packet_start  # crc_size is 1 if not is_nope and 0 if is_nope, just as packet_start
            buf = self.outstanding_buffer[: packet_size + packet_start + crc]
            self.outstanding_buffer = self.outstanding_buffer[
                packet_start + packet_size + crc :
            ]

            assert len(buf) == packet_start + packet_size + crc
            if crc:
                if self.recv_crc(buf) != 0:
                    LOGGER.error(
                        "Buffer %s doesn't match CRC, which should be %d but actually was %d",
                        buf,
                        self.recv_crc(buf),
                        buf[-1],
                    )
                    # Drop one byte and try synchronization again
                    self.outstanding_buffer = buf[1:] + self.outstanding_buffer
                    continue

            if len(buf) != 0:
                await self.__handle_packet(buf[packet_start:-crc])

    async def __handle_polling(self):
        """Handle read data from alarm."""

        if self.password is None:
            return

        while True:
            try:
                await self.send_request_zones()
                await asyncio.sleep(1)

                if (
                    self._read_timestamp is not None
                    and time.monotonic() - self._read_timestamp >= self._timeout
                ):
                    self.polling_task = None
                    LOGGER.error("Timeout error")
                    await self.__accept_new_connection()
                    return

            except OSError as ex:
                self.polling_task = None
                LOGGER.error("Connection error %s", ex)
                await self.__accept_new_connection()
                return
            except Exception as ex:
                self.polling_task = None
                LOGGER.error("Some unknown error %s", ex)
                await self.__accept_new_connection()
                raise

    async def __handle_read_from_stream(self):
        """Handle read data from alarm."""

        while True:
            self._read_timestamp = time.monotonic()
            data = await self.reader.read(4096)
            if self.reader.at_eof():
                self.reading_task = None
                LOGGER.error("Connection dropped by other side")
                await self.__accept_new_connection()
                return

            self.outstanding_buffer += data

            try:
                await self.__handle_data()
            except Exception as ex:
                self.read_task = None
                LOGGER.error("Some unknown error %s", ex)
                await self.__accept_new_connection()
                raise

    async def wait_connection(self) -> bool:
        """Test if we can authenticate with the host."""

        LOGGER.error(
            "Not connected to Alarm Panel. Waiting connection from Alarm Panel"
        )
        # print("Logged error", file=sys.stderr)
        # traceback.print_stack(file=sys.stderr)

        self.outstanding_buffer = bytes([])
        self.is_initialized = False
        self.update_event.clear()

        self.open_sensors = [None] * self.max_sensors
        self.partitions = [None] * self.max_partitions
        self.triggered_partitions = [False] * self.max_partitions
        self.triggered_sensors = [False] * self.max_sensors

        self.close()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.setblocking(False)
        self.socket.bind(("", self.port))
        self.socket.listen(1)

        # print ("Will call call_listeners", file=sys.stderr)
        self.__call_listeners()
        # print ("Called call_listeners", file=sys.stderr)

        loop = asyncio.get_running_loop()
        while True:
            try:
                (self.client_socket, _) = await asyncio.wait_for(
                    loop.sock_accept(self.socket), timeout=600
                )
                LOGGER.error("Connection accepted")
            except asyncio.TimeoutError:
                LOGGER.error(
                    "Timeout waiting on connection from Alarm Panel (60s). Retrying"
                )
                continue
            try:
                (self.reader, self.writer) = await asyncio.open_connection(
                    None, sock=self.client_socket
                )
            except asyncio.TimeoutError:
                LOGGER.error(
                    "Timeout opening connection from Alarm Panel (60s). Retrying"
                )
                continue
            # print("Connection from Alarm Panel established", file=sys.stderr)
            self.__call_listeners()
            break

        return True

    async def async_alarm_disarm(self, code=None):
        """Send disarm command."""

    async def async_alarm_arm_night(self, code=None):
        """Send disarm command."""
        for i in range(self.max_partitions):
            if CONF_NIGHT_PARTITION_LIST[i] in self.config_entry.data:
                if self.config_entry.data[CONF_NIGHT_PARTITION_LIST[i]]:
                    await self.send_arm_partition(i)
            else:
                await self.send_arm_partition(i)

    async def async_alarm_arm_away(self, code=None):
        """Send disarm command."""
        if self.config_entry.data[CONF_AWAY_MODE_ENABLED]:
            for i in range(self.max_partitions):
                if CONF_AWAY_PARTITION_LIST[i] in self.config_entry.data:
                    if self.config_entry.data[CONF_AWAY_PARTITION_LIST[i]]:
                        self.send_arm_partition(i)
                else:
                    self.send_arm_partition(i)

    async def async_alarm_arm_home(self, code=None):
        """Send disarm command."""
        if self.config_entry.data[CONF_HOME_MODE_ENABLED]:
            for i in range(self.max_partitions):
                if CONF_HOME_PARTITION_LIST[i] in self.config_entry.data:
                    if self.config_entry.data[CONF_HOME_PARTITION_LIST[i]]:
                        await self.send_arm_partition(i)
                else:
                    await self.send_arm_partition(i)

    def close(self):
        """Close and free resources."""
        if self.socket is not None:
            self.socket.close()
        if self.client_socket is not None:
            self.client_socket.close()
        if self.writer is not None:
            self.writer.close()

    async def async_update(self):
        """Asynchronously update hub state."""
        if self.polling_task is None:
            self.polling_task = asyncio.create_task(self.__handle_polling())
        if self.reading_task is None:
            self.reading_task = asyncio.create_task(self.__handle_read_from_stream())

        if not self.is_initialized:
            await self.update_event.wait()
            self.update_event.clear()

    async def wait_connection_and_update(self):
        """Call asynchronously wait_connection and then after a update."""
        await self.wait_connection()
        await self.async_update()

    async def __accept_new_connection(self):
        self._read_timestamp = None
        if self.polling_task is not None:
            self.polling_task.cancel()
            self.polling_task = None
        if self.reading_task is not None:
            self.reading_task.cancel()
            self.reading_task = None
        if self.client_socket is not None:
            self.client_socket.close()

        self.hass.async_create_task(self.wait_connection_and_update())

    def get_partitions(self):
        """Return partitions array."""
        return self.partitions

    def get_triggered_partitions(self):
        """Return partitions array."""
        return self.triggered_partitions

    def get_open_sensors(self):
        """Return motion sensors states."""
        return self.open_sensors

    def listen_event(self, listener):
        """Add object as listener."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listen_event(self, listener):
        """Add object as listener."""
        if listener in self.listeners:
            self.listeners.remove(listener)

    def __call_listeners(self):
        """Call all listeners."""
        # print ("__call_listeners: ", len(self.listeners), file=sys.stderr)
        for i in self.listeners:
            i.hub_update()

    @property
    def max_sensors(self):
        """Return the maximum number of sensors the platform may have."""
        return 48

    def is_sensor_configured(self, index):
        """Check if the numbered sensor is configured."""
        return True

    @property
    def max_partitions(self):
        """Return the maximum number of partitions the platform may have."""
        return 4

    def is_partition_configured(self, index):
        """Check if the numbered partition is configured."""
        return True


async def async_initialize_alarm(
    hass: HomeAssistant, alarm: AlarmHub, config: ConfigType
):
    """Call asynchronously wait_connection and update followed by entry setup."""
    LOGGER.error("async_intiialize_alarm")
    print("async_intiialize_alarm")

    await alarm.wait_connection_and_update()

    # for component in PLATFORMS:
    #     hass.async_create_task(
    #         hass.config_entries.async_forward_entry_setup(config, component)
    #     )

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Intelbras AMT Alarms component."""
    LOGGER.error("__init__ async_setup")

    if DOMAIN not in config:
        return True

    config = config[DOMAIN]

    alarm = AlarmHub(hass, {}, config.get(CONF_PORT), config.get(CONF_PASSWORD))
    hass.data[DOMAIN] = alarm

    await alarm.wait_connection_and_update()

    hass.helpers.discovery.load_platform('alarm_control_panel', DOMAIN, {}, config)

    #alarm_control_panel.async_setup(
    #hass.async_create_task(async_initialize_alarm(hass, alarm, config))

    # panels: list[Union[AlarmPanel, PartitionAlarmPanel]] = [AlarmPanel(alarm, entry)]
    # for i in range(alarm.max_partitions):
    #     panels.append(PartitionAlarmPanel(alarm, i))

    # for panel in panels:
    #     panel.update_state()

    # add_entities(panels)
    
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Intelbras AMT Alarms from a config entry."""
    LOGGER.error("async_setup_entry")
    print("async_setup_entry")

#     alarm = AlarmHub(hass, entry, entry.data["port"], entry.data["password"])
#     hass.data[DOMAIN][entry.entry_id] = alarm

#     hass.async_create_task(async_initialize_alarm(hass, alarm, entry))

#     return True

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the alarm platform."""
    print("setup_platform")
    LOGGER.error("setup_platform")
