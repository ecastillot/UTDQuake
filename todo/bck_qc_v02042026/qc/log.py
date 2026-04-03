# qc_log.py

class QCLog:
    """Class to store structured QC logs with cumulative counts."""

    def __init__(self):
        self.steps = []
        self.cumulative_removed = 0  # tracked automatically
        self.cumulative_per_phase = {}  # new dict

    def add_step(self, name, removed, thresholds=None, extra=None, phase=None):
        """
        Add a QC step. Updates both global and phase-specific cumulative counts.
        """
        self.cumulative_removed += removed
        if phase:
            self.cumulative_per_phase[phase] = self.cumulative_per_phase.get(phase, 0) + removed

        entry = {
            "name": name,
            "phase": phase,
            "removed": removed,
            "cumulative_removed": self.cumulative_removed,
            "cumulative_phase_removed": self.cumulative_per_phase.get(phase, None),
            "thresholds": thresholds or {},
        }
        if extra:
            entry.update(extra)
        self.steps.append(entry)

    def get_step(self, name):
        """Return the first step matching the name."""
        for step in self.steps:
            if step["name"] == name:
                return step
        return None

    def get_steps(self):
        """Return all steps."""
        return self.steps
    
    def get_steps_by_phase(self, phase):
        """Return all QC steps related to a specific phase."""
        return [step for step in self.steps if step.get("phase") == phase]

    def total_removed(self):
        """Return total removed across all steps."""
        return self.cumulative_removed

    def __repr__(self):
        summary = [f"QCLog: {len(self.steps)} steps, total removed: {self.cumulative_removed}"]
        for step in self.steps:
            summary.append(
                f" - {step['name']}: removed {step['removed']}, cumulative {step['cumulative_removed']}"
            )
        return "\n".join(summary)