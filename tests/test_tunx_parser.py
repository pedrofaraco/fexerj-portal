"""Unit tests for calculator.tunx_parser."""
import pathlib
import struct
import warnings

import pytest

from calculator.tunx_parser import (
    BIO_MARKER,
    BYE_SNR,
    PAIRING_MARKER,
    find_next_record,
    is_printable_utf16,
    parse_bio_section,
    parse_tunx,
    parse_tunx_from_bytes,
    read_field,
    skip_null,
    skip_to_binary_block,
    validate,
)

BINARY_DIR = pathlib.Path(__file__).parent / 'binary'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utf16_field(text):
    """Encode text as a [uint16 char_count][utf16-le chars] field."""
    encoded = text.encode('utf-16-le')
    return struct.pack('<H', len(text)) + encoded


# ---------------------------------------------------------------------------
# read_field
# ---------------------------------------------------------------------------

class TestReadField:
    def test_reads_simple_ascii(self):
        data = utf16_field("Silva")
        text, offset = read_field(data, 0)
        assert text == "Silva"
        assert offset == len(data)

    def test_reads_empty_string(self):
        data = utf16_field("")
        text, offset = read_field(data, 0)
        assert text == ""
        assert offset == 2

    def test_reads_accented_characters(self):
        data = utf16_field("Hervé")
        text, _ = read_field(data, 0)
        assert text == "Hervé"

    def test_reads_at_nonzero_offset(self):
        prefix = b'\xff\xff'
        data = prefix + utf16_field("Hugo")
        text, offset = read_field(data, 2)
        assert text == "Hugo"
        assert offset == 2 + 2 + 8  # prefix + char_count + 4 chars * 2 bytes


# ---------------------------------------------------------------------------
# skip_null
# ---------------------------------------------------------------------------

class TestSkipNull:
    def test_skips_null_terminator(self):
        data = b'\x00\x00\xAB\xCD'
        assert skip_null(data, 0) == 2

    def test_no_null_returns_same_offset(self):
        data = b'\x41\x00\xAB\xCD'
        assert skip_null(data, 0) == 0

    def test_only_first_byte_zero_no_skip(self):
        data = b'\x00\x41'
        assert skip_null(data, 0) == 0

    def test_at_end_of_data_no_skip(self):
        data = b'\x00'
        assert skip_null(data, 0) == 0


# ---------------------------------------------------------------------------
# is_printable_utf16
# ---------------------------------------------------------------------------

class TestIsPrintableUtf16:
    def test_printable_ascii_chars(self):
        data = "Hello".encode('utf-16-le')
        assert is_printable_utf16(data, 0, 5) is True

    def test_control_character_not_printable(self):
        data = struct.pack('<H', 0x0009)  # TAB
        assert is_printable_utf16(data, 0, 1) is False

    def test_high_unicode_not_printable(self):
        data = struct.pack('<H', 0x0410)  # Cyrillic А
        assert is_printable_utf16(data, 0, 1) is False

    def test_latin_extended_printable(self):
        data = struct.pack('<H', 0x00E9)  # é
        assert is_printable_utf16(data, 0, 1) is True

    def test_zero_char_count_returns_true(self):
        assert is_printable_utf16(b'', 0, 0) is True

    def test_out_of_bounds_returns_false(self):
        data = b'\x41'  # only 1 byte, but need 2 for one UTF-16 char
        assert is_printable_utf16(data, 0, 1) is False


# ---------------------------------------------------------------------------
# skip_to_binary_block
# ---------------------------------------------------------------------------

class TestSkipToBinaryBlock:
    def test_finds_zero_run(self):
        data = b'\x01\x02\x03' + b'\x00' * 8 + b'\xFF'
        assert skip_to_binary_block(data, 0, len(data)) == 3

    def test_already_at_zero_run(self):
        data = b'\x00' * 8 + b'\xFF'
        assert skip_to_binary_block(data, 0, len(data)) == 0

    def test_returns_bio_end_if_no_run_found(self):
        data = b'\x01\x02\x03\x04\x05'
        assert skip_to_binary_block(data, 0, len(data)) == len(data)

    def test_short_zero_run_not_enough(self):
        data = b'\x01' + b'\x00' * 4 + b'\x01' + b'\x00' * 8 + b'\xFF'
        assert skip_to_binary_block(data, 0, len(data)) == 6


# ---------------------------------------------------------------------------
# find_next_record
# ---------------------------------------------------------------------------

class TestFindNextRecord:
    def make_two_fields(self, first, last):
        return utf16_field(first) + utf16_field(last)

    def test_finds_valid_two_field_record(self):
        data = self.make_two_fields("Tiago", "Rocha")
        assert find_next_record(data, 0, len(data)) == 0

    def test_skips_single_field_entry(self):
        single = utf16_field("NAT") + utf16_field("")
        two_field = self.make_two_fields("Tiago", "Rocha")
        data = single + two_field
        assert find_next_record(data, 0, len(data)) == len(single)

    def test_returns_bio_end_when_no_record(self):
        data = b'\x00' * 20
        assert find_next_record(data, 0, len(data)) == len(data)

    def test_skips_nonprintable_bytes(self):
        garbage = b'\xFF\xFF\x00\x00'
        valid = self.make_two_fields("Clara", "Melo")
        data = garbage + valid
        assert find_next_record(data, 0, len(data)) == len(garbage)


# ---------------------------------------------------------------------------
# parse_bio_section
# ---------------------------------------------------------------------------

def make_player_bytes(first, last, abbrev, title, player_id, club, fed, asterisk_prefix=False):
    """Build a minimal bio record in Swiss Manager binary format."""
    record = utf16_field(first) + utf16_field(last)
    if asterisk_prefix:
        record += utf16_field('*')
    else:
        record += b'\x00\x00'
    record += utf16_field(abbrev)
    record += utf16_field(title)
    record += utf16_field(player_id)
    record += b'\x00\x00'
    record += b'\x00\x00\x00\x00'
    record += utf16_field(club)
    record += utf16_field(fed)
    record += b'\x00\x00'
    record += b'\x00' * 40
    return record


class TestParseBioSection:
    def _wrap(self, player_bytes):
        return BIO_MARKER + player_bytes + PAIRING_MARKER

    def test_normal_record_parsed(self):
        data = self._wrap(make_player_bytes('Tiago', 'Rocha', 'T. Rocha', '', '1234', 'Club', 'BRA'))
        bio = parse_bio_section(data)
        assert len(bio) == 1
        assert bio[1]['fexerj_id'] == '1234'
        assert bio[1]['name'] == 'Rocha, Tiago'

    def test_asterisk_prefix_record_parsed(self):
        player = make_player_bytes('Hugo', 'Viana', 'H. Viana', '', '5523', 'Club', 'BRA', asterisk_prefix=True)
        data = self._wrap(player)
        bio = parse_bio_section(data)
        assert len(bio) == 1
        assert bio[1]['fexerj_id'] == '5523'

    def test_asterisk_and_normal_records_both_parsed(self):
        player1 = make_player_bytes('Sergio', 'Pinto', 'S. Pinto', '', '5221', 'Club', 'BRA')
        player2 = make_player_bytes('Hugo', 'Viana', 'H. Viana', '', '5523', 'Club', 'BRA', asterisk_prefix=True)
        data = self._wrap(player1 + player2)
        bio = parse_bio_section(data)
        assert len(bio) == 2
        assert bio[1]['fexerj_id'] == '5221'
        assert bio[2]['fexerj_id'] == '5523'


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_missing_bio_marker_raises(self):
        data = PAIRING_MARKER + b'\x00' * 100
        with pytest.raises(ValueError, match="bio marker"):
            validate("test.TUNX", data, {1: {'name': 'A', 'fexerj_id': ''}}, [])

    def test_missing_pairing_marker_raises(self):
        data = BIO_MARKER + b'\x00' * 100
        with pytest.raises(ValueError, match="pairing marker"):
            validate("test.TUNX", data, {1: {'name': 'A', 'fexerj_id': ''}}, [])

    def test_empty_bio_raises(self):
        data = BIO_MARKER + b'\x00' * 50 + PAIRING_MARKER + b'\x00' * 50
        with pytest.raises(ValueError, match="no players"):
            validate("test.TUNX", data, {}, [])

    def test_unknown_result_codes_warn(self):
        pairing_record = struct.pack('<HHH', 1, 2, 0xFF) + b'\x00' * 15
        data = BIO_MARKER + b'\x00' * 10 + PAIRING_MARKER + pairing_record
        bio = {1: {'name': 'A', 'fexerj_id': ''}, 2: {'name': 'B', 'fexerj_id': ''}}
        with pytest.warns(UserWarning, match="unknown result codes"):
            validate("test.TUNX", data, bio, [])

    def test_out_of_range_snr_warns(self):
        pairing_record = struct.pack('<HHH', 1, 2, 1) + b'\x00' * 15
        data = BIO_MARKER + b'\x00' * 10 + PAIRING_MARKER + pairing_record
        bio = {1: {'name': 'A', 'fexerj_id': ''}}  # SNR 2 missing
        with pytest.warns(UserWarning, match="unknown SNRs"):
            validate("test.TUNX", data, bio, [(1, 2, 1.0)])

    def test_valid_data_raises_nothing(self):
        pairing_record = struct.pack('<HHH', 1, 2, 1) + b'\x00' * 15
        data = BIO_MARKER + b'\x00' * 10 + PAIRING_MARKER + pairing_record
        bio = {1: {'name': 'A', 'fexerj_id': ''}, 2: {'name': 'B', 'fexerj_id': ''}}
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            validate("test.TUNX", data, bio, [(1, 2, 1.0)])


# ---------------------------------------------------------------------------
# parse_tunx_from_bytes — integration tests against real binary files
# ---------------------------------------------------------------------------

TUNX_T1_DATA  = (BINARY_DIR / 'swiss_system_18players.TUNX').read_bytes()
TURX_T6_DATA  = (BINARY_DIR / 'round_robin_6players.TURX').read_bytes()
TUMX_T8_DATA  = (BINARY_DIR / 'swiss_team_93players.TUMX').read_bytes()
TUNX_T23_DATA = (BINARY_DIR / 'swiss_system_51players.TUNX').read_bytes()


class TestParseTunxFromBytesIntegration:
    def test_t1_player_count(self):
        bio, _ = parse_tunx_from_bytes(TUNX_T1_DATA)
        assert len(bio) == 18

    def test_t1_known_fexerj_ids(self):
        bio, _ = parse_tunx_from_bytes(TUNX_T1_DATA)
        assert bio[1]['fexerj_id'] == '1078'
        assert bio[11]['fexerj_id'] == '3128'

    def test_t1_snr18_has_no_id(self):
        bio, _ = parse_tunx_from_bytes(TUNX_T1_DATA)
        assert bio[18]['fexerj_id'] == ''

    def test_t1_name_format(self):
        bio, _ = parse_tunx_from_bytes(TUNX_T1_DATA)
        assert ',' in bio[1]['name']

    def test_t1_game_count(self):
        _, games = parse_tunx_from_bytes(TUNX_T1_DATA)
        assert len(games) == 42

    def test_t1_total_points_equal_number_of_games(self):
        _, games = parse_tunx_from_bytes(TUNX_T1_DATA)
        total = sum(score + (1.0 - score) for _, _, score in games)
        assert abs(total - len(games)) < 0.001

    def test_t1_no_bye_in_games(self):
        _, games = parse_tunx_from_bytes(TUNX_T1_DATA)
        for snr_a, snr_b, _ in games:
            assert snr_b != BYE_SNR
            assert snr_a != 0
            assert snr_b != 0

    def test_t1_scores_are_valid(self):
        _, games = parse_tunx_from_bytes(TUNX_T1_DATA)
        for _, _, score in games:
            assert score in (0.0, 0.5, 1.0)

    def test_turx_t6_player_count(self):
        bio, _ = parse_tunx_from_bytes(TURX_T6_DATA)
        assert len(bio) == 6

    def test_turx_t6_all_ids_present(self):
        bio, _ = parse_tunx_from_bytes(TURX_T6_DATA)
        assert all(info['fexerj_id'] for info in bio.values())

    def test_tumx_t8_player_count(self):
        bio, _ = parse_tunx_from_bytes(TUMX_T8_DATA)
        assert len(bio) == 93

    def test_tumx_t8_scores_are_valid(self):
        _, games = parse_tunx_from_bytes(TUMX_T8_DATA)
        for _, _, score in games:
            assert score in (0.0, 0.5, 1.0)

    def test_tumx_t8_no_bye_in_games(self):
        _, games = parse_tunx_from_bytes(TUMX_T8_DATA)
        for snr_a, snr_b, _ in games:
            assert snr_b != BYE_SNR
            assert snr_a != 0
            assert snr_b != 0

    def test_t23_all_players_parsed_despite_asterisk_prefix(self):
        bio, _ = parse_tunx_from_bytes(TUNX_T23_DATA)
        assert len(bio) == 51

    def test_t23_asterisk_prefix_player_has_correct_id(self):
        bio, _ = parse_tunx_from_bytes(TUNX_T23_DATA)
        assert bio[36]['fexerj_id'] == '5523'


# ---------------------------------------------------------------------------
# parse_tunx — file-based wrapper still works
# ---------------------------------------------------------------------------

class TestParseTunxFileBased:
    def test_file_based_gives_same_result_as_bytes(self):
        filepath = str(BINARY_DIR / 'round_robin_6players.TURX')
        bio_file, games_file = parse_tunx(filepath)
        bio_bytes, games_bytes = parse_tunx_from_bytes(TURX_T6_DATA)
        assert bio_file == bio_bytes
        assert games_file == games_bytes
