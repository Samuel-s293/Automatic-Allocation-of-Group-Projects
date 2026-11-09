from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


class InstanceError(ValueError):
    pass


@dataclass(frozen=True)
class Project:
    id: str
    min_size: int
    max_size: int

    def __post_init__(self):
        if self.min_size < 1:
            raise InstanceError(f"project {self.id}: min must be at least 1")
        if self.max_size < self.min_size:
            raise InstanceError(f"project {self.id}: max is smaller than min")


@dataclass(frozen=True)
class Instance:
    projects: dict[str, Project]
    # student id -> project ids, best first
    preferences: dict[str, tuple[str, ...]]

    def __post_init__(self):
        if not self.projects:
            raise InstanceError("there are no projects")
        if not self.preferences:
            raise InstanceError("there are no students")

        for student, ranking in self.preferences.items():
            if not ranking:
                raise InstanceError(f"student {student}: no projects ranked")
            for p in ranking:
                if p not in self.projects:
                    raise InstanceError(f"student {student}: unknown project {p}")
            if len(set(ranking)) != len(ranking):
                raise InstanceError(
                    f"student {student}: ranks the same project more than once"
                )

    @property
    def students(self):
        return list(self.preferences)

    def rank_of(self, student, project):
        # 1 = first choice, None if they didn't rank it
        ranking = self.preferences[student]
        if project not in ranking:
            return None
        return ranking.index(project) + 1


def load_instance(projects_path, preferences_path):
    projects = load_projects(projects_path)
    preferences = load_preferences(preferences_path)
    return Instance(projects, preferences)


def load_projects(path):
    header, rows = read_csv(path)
    if header != ["project_id", "min", "max"]:
        raise InstanceError(f"{path}: header must be project_id,min,max")

    projects = {}
    for where, (pid, lo, hi) in padded_rows(path, rows, len(header)):
        check_id(pid, projects, "project", where)
        projects[pid] = Project(pid, to_int(lo, where), to_int(hi, where))
    return projects


def load_preferences(path):
    header, rows = read_csv(path)
    expected = ["student_id"] + ["rank" + str(i) for i in range(1, len(header))]
    if len(header) < 2 or header != expected:
        raise InstanceError(f"{path}: header must be student_id,rank1,rank2,...")

    preferences = {}
    for where, (sid, *cells) in padded_rows(path, rows, len(header)):
        check_id(sid, preferences, "student", where)

        # trailing blanks are fine, but a gap like P1,,P3 isn't -
        # we wouldn't know what rank P3 is supposed to be
        ranking = []
        for i, cell in enumerate(cells):
            if not cell:
                if any(cells[i:]):
                    raise InstanceError(f"{where}: blank cell between ranked projects")
                break
            ranking.append(cell)

        preferences[sid] = tuple(ranking)
    return preferences


def read_csv(path):
    # utf-8-sig so Excel's BOM doesn't end up stuck to the first header
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            cells = [c.strip() for c in row]
            if any(cells):  # skip blank lines
                rows.append((reader.line_num, cells))

    if not rows:
        raise InstanceError(f"{path}: file is empty")
    return rows[0][1], rows[1:]


def padded_rows(path, rows, width):
    # Excel drops trailing empty cells, so pad short rows out to the header width
    for line, cells in rows:
        where = f"{path}:{line}"
        if len(cells) > width:
            raise InstanceError(f"{where}: more cells than header columns")
        yield where, cells + [""] * (width - len(cells))


def check_id(new_id, seen, kind, where):
    if not new_id:
        raise InstanceError(f"{where}: missing {kind} ID")
    if new_id in seen:
        raise InstanceError(f"{where}: duplicate {kind} ID {new_id}")


def to_int(text, where):
    try:
        return int(text)
    except ValueError:
        raise InstanceError(f"{where}: {text!r} is not a whole number") from None