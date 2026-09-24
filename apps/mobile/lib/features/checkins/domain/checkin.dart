/// Optional, student-initiated check-in about academic support needs.
///
/// The options are practical study needs only. The app never asks about, infers or
/// labels health or mental-health conditions (docs/research/project-scope.md).
enum SupportNeed {
  academicDifficulty('academic_difficulty', 'Understanding course material'),
  courseDifficulty('course_difficulty', 'A specific course feels hard'),
  workload('workload', 'Too much work at once'),
  timeManagement('time_management', 'Managing my time'),
  studyChallenges('study_challenges', 'Studying effectively'),
  financialDifficulty('financial_difficulty', 'Money worries affecting my studies');

  const SupportNeed(this.dbValue, this.label);

  final String dbValue;
  final String label;
}

const int maxCheckinCommentLength = 500;

/// A validated check-in ready to submit.
class CheckinDraft {
  CheckinDraft({required Set<SupportNeed> needs, required this.wantsContact, String? comment})
      : needs = Set.unmodifiable(needs),
        comment = (comment == null || comment.trim().isEmpty) ? null : comment.trim();

  final Set<SupportNeed> needs;
  final bool wantsContact;
  final String? comment;

  /// Mirrors the database rules: something must be said, and the comment is at most 500 characters.
  String? get validationError {
    if (needs.isEmpty && !wantsContact && comment == null) {
      return 'Choose at least one option, ask to be contacted, or add a comment.';
    }
    if ((comment?.length ?? 0) > maxCheckinCommentLength) {
      return 'Keep the comment to $maxCheckinCommentLength characters or fewer.';
    }
    return null;
  }

  Map<String, dynamic> toInsert(String studentId) => {
        'student_id': studentId,
        'support_needs': [for (final n in SupportNeed.values) if (needs.contains(n)) n.dbValue],
        'wants_contact': wantsContact,
        'comment': comment,
      };
}
