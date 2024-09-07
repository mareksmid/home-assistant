from random import choice
from homeassistant.components.media_source import async_browse_media


@event_trigger('play')
def play() -> None:
    # 'Seizo Azuma' disk/:22$15357
    # 'Suzuki Piano School, Vol. 1', 2 'disk/:22$15359', 'disk/:22$15364'
    songs =  [f'media-source://{s.domain}/{s.identifier}' for s in async_browse_media(hass, 'media-source://dlna_dms/disk/:22$15359').children]
    song = choice(songs)
    log.info(f'Playing {song}')
    hass.services.call('media_player', 'play_media', {'entity_id': 'media_player.wa250', 'media_content_id': song})
