import csv
import io
import math
from enum import Enum

from .tunx_parser import parse_tunx_from_bytes
from .name_utils import normalize_name, name_similarity

_CSV_DELIMITER = ';'
_RATING_LIST_HEADER = 'Id_No;Id_CBX;Title;Name;Rtg_Nat;ClubName;Birthday;Sex;Fed;TotalNumGames;SumOpponRating' \
                      ';TotalPoints'
# -- Audit File Columns --
# Id_Fexerj = ID of the player within FEXERJ
# Name = Name of the player
# No = Number of the player within Chess Result tournament
# Ro = Rating before tournament
# Ind = Total games before tournament
# K = K before tournament
# PG = Points against opponents on valid games in the current tournament
# N = Valid games in the current tournament
# Erm = SUM of opponents' ratings in the current tournament
# Rm = Average rating of opponents in the current tournament
# Dif = Difference between Ro and Rm
# We = Nwe divided by N (zero if N is zero)
# Nwe = Expected points in the current tournament
# Dw = Points above expected in the current tournament
# kDw = K * Dw
# Rn = New rating
# Nind = New total games
# P = PG / N
# Calc_Rule = Calculation Rule used (NORMAL, TEMPORARY, RATING_PERFORMANCE or DOUBLE_K)
_AUDIT_FILE_HEADER = 'Id_Fexerj;Name;No;Ro;Ind;K;PG;N;Erm;Rm;Dif;We;Nwe;Dw;kDw;Rn;Nind;P;Calc_Rule'
_MAX_NUM_GAMES_TEMP_RATING = 15


class TournamentType(Enum):
    SS = 'SS'  # Swiss Single
    RR = 'RR'  # Round Robin
    ST = 'ST'  # Swiss Team


class CalcRule(Enum):
    TEMPORARY = 'TEMPORARY'
    RATING_PERFORMANCE = 'RATING_PERFORMANCE'
    DOUBLE_K = 'DOUBLE_K'
    NORMAL = 'NORMAL'


_K_STARTING_NUM_GAMES = [(30, 0),  # grampo
                         (25, _MAX_NUM_GAMES_TEMP_RATING),  # 15
                         (15, 40),
                         (10, 80)]


class FexerjRatingCycle:
    def __init__(self, tournaments_csv: str, first_item: int, items_to_process: int,
                 initial_rating_csv: str, binary_files: dict):
        """
        Args:
            tournaments_csv: Content of tournaments.csv as a string.
            first_item: 1-based ordinal of the first tournament to process.
            items_to_process: Number of tournaments to process.
            initial_rating_csv: Content of the starting players/rating list CSV as a string.
            binary_files: Mapping of filename to bytes for each binary tournament file,
                          e.g. {"1-12345.TUNX": b"...", "2-67890.TURX": b"..."}.
        """
        self.tournaments_csv = tournaments_csv
        self.first_item = first_item
        self.items_to_process = items_to_process
        self.initial_rating_csv = initial_rating_csv
        self.rating_list = {}
        self.cbx_to_fexerj = {}
        self.binary_files = binary_files

    def run_cycle(self) -> dict:
        """Run the rating cycle and return all output files.

        Returns:
            A dict mapping output filename to CSV content string, e.g.:
            {
                "RatingList_after_1.csv": "...",
                "Audit_of_Tournament_1.csv": "...",
                ...
            }
        """
        output_files = {}
        reader = csv.reader(io.StringIO(self.tournaments_csv), delimiter=_CSV_DELIMITER)
        tournaments = list(reader)[1:]  # skip header row

        current_rating_csv = self.initial_rating_csv

        for tournament_row in tournaments:
            if int(tournament_row[0]) in range(self.first_item, self.first_item + self.items_to_process):
                rating_list_filename = "RatingList_after_%s.csv" % tournament_row[0]
                audit_filename = "Audit_of_Tournament_%s.csv" % tournament_row[0]

                self.rating_list = {}
                self.cbx_to_fexerj = {}
                self.get_rating_list(current_rating_csv)

                try:
                    trn_type = TournamentType(tournament_row[4])
                except ValueError:
                    raise ValueError(
                        f"Tournament {tournament_row[0]}: '{tournament_row[4]}' is not a valid TournamentType"
                    )

                if trn_type == TournamentType.SS:
                    tournament = SwissSingleTournament(self, tournament_row)
                elif trn_type == TournamentType.RR:
                    tournament = RoundRobinTournament(self, tournament_row)
                elif trn_type == TournamentType.ST:
                    tournament = SwissTeamTournament(self, tournament_row)

                tournament.load_player_list()
                tournament.complete_players_info()
                tournament.calculate_players_ratings()

                current_rating_csv = tournament.write_new_ratings_list()
                output_files[rating_list_filename] = current_rating_csv
                output_files[audit_filename] = tournament.write_tournament_audit()

        return output_files

    def get_rating_list(self, rating_csv: str):
        reader = csv.reader(io.StringIO(rating_csv), delimiter=_CSV_DELIMITER)
        next(reader, None)  # Skip the headers
        for row in reader:
            player = FexerjPlayer(int(row[0]),  # ID FEXERJ
                                  row[1],  # ID CBX
                                  row[2],  # TITLE
                                  row[3],  # NAME
                                  int(row[4]),  # RATING
                                  row[5],  # CLUB
                                  row[6],  # BIRTHDAY
                                  row[7],  # SEX
                                  row[8],  # FEDERATION
                                  int(row[9]),  # TOTAL NUM OF GAMES
                                  row[10],  # SUM OF OPPONENT RATINGS
                                  row[11])  # POINTS AGAINST OPPONENTS
            self.rating_list.update({int(row[0]): player})
            if len(row[1]) > 0:
                self.cbx_to_fexerj[int(row[1])] = int(row[0])


class FexerjPlayer:
    def __init__(self, id_fexerj, id_cbx, title, name, last_rating, club, birthday, sex, federation, total_games,
                 sum_opponents_ratings, points_against_opponents):
        self.id_fexerj = id_fexerj
        self.id_cbx = id_cbx
        self.title = title
        self.name = name
        self.last_rating = last_rating
        self.club = club
        self.birthday = birthday
        self.sex = sex
        self.federation = federation
        self.total_games = total_games
        self.sum_opponents_ratings = sum_opponents_ratings
        self.points_against_opponents = points_against_opponents


class TournamentPlayer:
    def __init__(self, tournament):
        self.snr = 0
        self.name = ""
        self.id = 0
        self.opponents = {}
        self.tournament = tournament
        self.is_unrated = None
        self.is_temp = None
        self.last_k = None
        self.last_rating = None
        self.last_total_games = None
        self.last_sum_oppon_ratings = None
        self.last_pts_against_oppon = None
        self.this_pts_against_oppon = None
        self.this_sum_oppon_ratings = None
        self.this_avg_oppon_rating = None
        self.this_games = None
        self.this_score = None
        self.this_expected_points = None
        self.this_points_above_expected = None
        self.new_rating = None
        self.new_total_games = None
        self.new_avg_oppon_rating = None
        self.new_sum_oppon_ratings = None
        self.new_pts_against_oppon = None
        self.calc_rule = None

    def add_opponent(self, sno, name, result):
        result_map = {"1": 1.0, "0": 0.0, "½": 0.5, "K": None}
        result_char = result[-1] if result else ""
        if result_char not in result_map:
            raise ValueError(f"Unexpected result '{result_char}' for opponent {name} (sno={sno})")
        if result_map[result_char] is not None:
            self.opponents[sno] = [name, result_map[result_char]]

    def resolve_id(self, raw_id):
        """Return the FEXERJ ID as int. Raises ValueError when raw_id is empty."""
        fexerj_id = int(raw_id) if raw_id else 0
        if fexerj_id:
            return fexerj_id
        raise ValueError(
            f"Player '{self.name}' (starting rank {self.snr}) has no FEXERJ ID in the binary file. "
            f"Please fix the Swiss Manager file and re-export before uploading."
        )

    def keep_current_rating(self):
        self.new_rating = self.last_rating
        self.new_total_games = self.last_total_games
        self.new_sum_oppon_ratings = self.last_sum_oppon_ratings
        self.new_pts_against_oppon = self.last_pts_against_oppon

    def calculate_new_rating(self, is_fexerj_tournament):
        # Step 1: Discard unrated opponents with no usable new rating, or all unrated opponents if the current player is also unrated.
        invalid_opponents = []
        for k, tp_oppon in self.opponents.items():
            if tp_oppon[0].is_unrated:
                if (self.is_unrated
                        or not tp_oppon[0].new_rating):
                    invalid_opponents.append(k)
        for i in invalid_opponents:
            del self.opponents[i]

        # Step 2: Return early if there are no valid games, or if the player is unrated and scored zero points.
        self.this_games = len(self.opponents)
        if (self.this_games == 0
                or (self.is_unrated and self.this_pts_against_oppon == 0)):
            self.keep_current_rating()
            return

        # Step 3: Accumulate opponent ratings and points scored, using new_rating for unrated opponents and for temp opponents when the current player is established.
        self.this_sum_oppon_ratings = 0
        self.this_pts_against_oppon = 0
        for snr_opp, oppon in self.opponents.items():
            if oppon[0].is_unrated:
                self.this_sum_oppon_ratings += oppon[0].new_rating
            elif oppon[0].is_temp and not (self.is_unrated or self.is_temp):  # only when the current player is established
                self.this_sum_oppon_ratings += oppon[0].new_rating
            else:
                self.this_sum_oppon_ratings += oppon[0].last_rating
            self.this_pts_against_oppon += oppon[1]
        if self.is_unrated and self.this_pts_against_oppon == 0:
            self.keep_current_rating()
            return

        # Step 4: Compute expected points and how many points the player scored above expectation.
        self.last_k = self.get_current_k()
        self.this_avg_oppon_rating = self.this_sum_oppon_ratings / self.this_games
        rating_diff = self.this_avg_oppon_rating - self.last_rating
        self.this_expected_points = self.this_games / (1.0 + 10.0 ** (rating_diff / 400.0))
        self.this_points_above_expected = (self.this_pts_against_oppon - self.this_expected_points)
        self.new_total_games = self.last_total_games + self.this_games

        # Step 5: Determine the calculation rule and apply it to compute the new rating.
        self.calc_rule = self.get_calculation_rule(is_fexerj_tournament)
        {
            CalcRule.TEMPORARY: self.apply_temporary_rule,
            CalcRule.RATING_PERFORMANCE: self.apply_rating_performance_rule,
            CalcRule.DOUBLE_K: self.apply_k_rule,
            CalcRule.NORMAL: self.apply_k_rule,
        }[self.calc_rule]()

    def apply_temporary_rule(self):
        if (self.this_games + self.last_total_games) == 0:
            pass
        else:
            self.new_sum_oppon_ratings = self.last_sum_oppon_ratings + self.this_sum_oppon_ratings
            self.new_avg_oppon_rating = self.new_sum_oppon_ratings / self.new_total_games
            self.new_pts_against_oppon = self.last_pts_against_oppon + self.this_pts_against_oppon
            self.new_rating = round(self.get_performance_rating(self.new_avg_oppon_rating, self.new_total_games,
                                                                self.new_pts_against_oppon))

    def apply_rating_performance_rule(self):
        self.this_avg_oppon_rating = self.this_sum_oppon_ratings / self.this_games
        performance_rating = self.get_performance_rating(self.this_avg_oppon_rating, self.this_games,
                                                         self.this_pts_against_oppon)
        self.new_rating = round(self.last_rating + (performance_rating - self.last_rating) / 2)

    def apply_k_rule(self):
        rating_gain = (1 + int(self.calc_rule == CalcRule.DOUBLE_K)) * self.last_k * self.this_points_above_expected
        rating_gain_rounded = round(rating_gain)
        self.new_rating = max(self.last_rating + rating_gain_rounded, 1)

    def get_calculation_rule(self, is_fexerj_tournament):
        if self.is_temp or self.is_unrated:
            return CalcRule.TEMPORARY
        elif self.check_rating_performance_rule() and is_fexerj_tournament:
            return CalcRule.RATING_PERFORMANCE
        elif self.check_double_k_rule():
            return CalcRule.DOUBLE_K
        return CalcRule.NORMAL

    def check_rating_performance_rule(self):
        if self.this_games < 5:
            return False
        elif self.this_games == 5:
            return self.this_points_above_expected >= 1.84
        elif self.this_games == 6:
            return self.this_points_above_expected >= 2.02
        elif self.this_games == 7:
            return self.this_points_above_expected >= 2.16
        else:
            print("WARNING: Unknown condition for RP rule with more than 7 games. Assuming FALSE for Rating Performance.")
            return False

    def check_double_k_rule(self):
        if self.this_games < 4:
            return False
        elif self.this_games == 4:
            return self.this_points_above_expected >= 1.65
        elif self.this_games == 5:
            return self.this_points_above_expected >= 1.43
        elif self.this_games == 6:
            return self.this_points_above_expected >= 1.56
        elif self.this_games == 7:
            return self.this_points_above_expected >= 1.69
        else:
            print("WARNING: Unknown condition for DK rule with more than 7 games. Assuming FALSE for Double K.")
            return False

    def get_current_k(self):
        current_k = None
        for (k, starting_num_games) in _K_STARTING_NUM_GAMES:
            if self.last_total_games >= starting_num_games:
                current_k = k
        if current_k is None:
            raise ValueError(f"Could not determine K factor for player with {self.last_total_games} total games.")
        return current_k

    def get_performance_rating(self, avg_oppon_rating, num_valid_games, total_num_points):
        # In case of perfect results, consider score as if there was an extra game that ended in a draw.
        score = total_num_points / num_valid_games
        if score == 1.0:
            score = (num_valid_games + 0.5) / (num_valid_games + 1.0)
        elif score == 0.0:
            score = 0.5 / (num_valid_games + 1.0)
        return avg_oppon_rating + 400.0 * math.log10(score / (1.0 - score))


class Tournament:
    def __init__(self, rating_cycle, tournament):
        self.ord = int(tournament[0])
        self.id = int(tournament[1])
        self.name = tournament[2]
        self.date_end = tournament[3]
        self.type = tournament[4]
        self.is_irt = int(tournament[5])
        self.is_fexerj = int(tournament[6])
        ext_map = {'SS': 'TUNX', 'RR': 'TURX', 'ST': 'TUMX'}
        ext = ext_map.get(tournament[4], 'TUNX')
        binary_filename = f"{tournament[0]}-{tournament[1]}.{ext}"
        if binary_filename not in rating_cycle.binary_files:
            raise ValueError(
                f"Binary file '{binary_filename}' not found in uploaded files. "
                f"Please upload all required .TUNX/.TURX/.TUMX files."
            )
        self.binary_data = rating_cycle.binary_files[binary_filename]
        self.players = {}
        self.unrated_keys = []
        self.temp_keys = []
        self.established_keys = []
        self.rating_cycle = rating_cycle

    def complete_players_info(self):
        for snr, tp in self.players.items():
            if self.is_irt:
                fp = self.rating_cycle.rating_list[self.rating_cycle.cbx_to_fexerj[tp.id]]
            else:
                fp = self.rating_cycle.rating_list[tp.id]
            tp.last_rating = int(fp.last_rating)
            tp.last_total_games = int(fp.total_games)
            tp.last_sum_oppon_ratings = int(fp.sum_opponents_ratings)
            tp.last_pts_against_oppon = float(fp.points_against_opponents)
            if tp.last_total_games == 0:
                self.unrated_keys.append(snr)
                tp.is_unrated = True
            elif tp.last_total_games < _MAX_NUM_GAMES_TEMP_RATING:
                self.temp_keys.append(snr)
                tp.is_temp = True
            else:
                self.established_keys.append(snr)

        # Replace opponent name/score entries with TournamentPlayer references
        for snr, tp in self.players.items():
            tp.opponents = {opp_snr: [self.players[opp_snr], data[1]] for opp_snr, data in tp.opponents.items()}

    def calculate_players_ratings(self):
        for k in self.unrated_keys:
            self.players[k].calculate_new_rating(self.is_fexerj)
        for k in self.temp_keys:
            self.players[k].calculate_new_rating(self.is_fexerj)
        for k in self.established_keys:
            self.players[k].calculate_new_rating(self.is_fexerj)

    def write_new_ratings_list(self) -> str:
        for player in self.players.values():
            if self.is_irt:
                fp = self.rating_cycle.rating_list[self.rating_cycle.cbx_to_fexerj[player.id]]
            else:
                fp = self.rating_cycle.rating_list[player.id]
            fp.last_rating = player.new_rating
            fp.total_games = player.new_total_games
            if player.new_total_games < _MAX_NUM_GAMES_TEMP_RATING:
                fp.sum_opponents_ratings = player.new_sum_oppon_ratings
                fp.points_against_opponents = player.new_pts_against_oppon
            else:
                fp.sum_opponents_ratings = 0
                fp.points_against_opponents = 0

        buf = io.StringIO()
        print(_RATING_LIST_HEADER, file=buf)
        for key, player in self.rating_cycle.rating_list.items():
            line_list = [str(player.id_fexerj),
                         str(player.id_cbx),
                         player.title,
                         player.name,
                         str(player.last_rating),
                         player.club,
                         player.birthday,
                         player.sex,
                         player.federation,
                         str(player.total_games),
                         str(player.sum_opponents_ratings),
                         str(player.points_against_opponents)]
            print(_CSV_DELIMITER.join(line_list), file=buf)
        return buf.getvalue()

    def load_player_list(self):
        bio, games = parse_tunx_from_bytes(self.binary_data, name=f"{self.ord}-{self.id}")

        for snr, info in bio.items():
            tp = TournamentPlayer(self)
            tp.snr = snr
            tp.name = info['name']
            tp.id = tp.resolve_id(info['fexerj_id'])
            self.players[snr] = tp

        for snr_a, snr_b, score_a in games:
            if snr_a in self.players and snr_b in self.players:
                self.players[snr_a].opponents[snr_b] = [self.players[snr_b].name, score_a]
                self.players[snr_b].opponents[snr_a] = [self.players[snr_a].name, 1.0 - score_a]

    def write_tournament_audit(self) -> str:
        buf = io.StringIO()
        print(_AUDIT_FILE_HEADER, file=buf)
        for snr, tp in self.players.items():
            line_list = [str(tp.id),
                         tp.name,
                         str(snr),
                         str(tp.last_rating),
                         str(tp.last_total_games),
                         str(tp.last_k),
                         str(tp.this_pts_against_oppon),
                         str(tp.this_games),
                         str(tp.this_sum_oppon_ratings),
                         str(float(tp.this_avg_oppon_rating or 0)),
                         str(tp.last_rating - float(tp.this_avg_oppon_rating or 0)),
                         str(None if tp.this_games == 0 else (float(tp.this_expected_points or 0) / tp.this_games)),
                         str(float(tp.this_expected_points or 0)),
                         str(float(tp.this_points_above_expected or 0)),
                         str(int(tp.last_k or 0) * float(tp.this_points_above_expected or 0)),
                         str(tp.new_rating),
                         str(tp.new_total_games),
                         str(None if tp.this_games == 0 else float(tp.this_pts_against_oppon or 0) / tp.this_games),
                         str(tp.calc_rule.value) if tp.calc_rule is not None else str(None)]
            print(_CSV_DELIMITER.join(line_list), file=buf)
        return buf.getvalue()


class SwissSingleTournament(Tournament):
    pass


class RoundRobinTournament(Tournament):
    pass


class SwissTeamTournament(Tournament):
    pass
