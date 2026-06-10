// lib/features/deals/data/deals_models.dart
//
// Deal Room data models — manual fromJson (mirrors features/meetings/data/
// meetings_models.dart). DealStage collapses the backend lifecycle statuses
// into the member-friendly buckets from the design spec filter chips:
// Incubation · Draft/Pipeline · Under review · Summit-ready · Deal room ·
// Committed/Implemented. Enum order tracks funnel progress so chip color and
// the "Summit-ready+" StatTile can key off the index.

/// Member-facing stage buckets, ordered by funnel progress.
enum DealStage { incubation, pipeline, underReview, summitReady, dealRoom, committed }

extension DealStageX on DealStage {
  /// Member-friendly chip/label text for this bucket.
  String get label => switch (this) {
        DealStage.incubation => 'Incubation',
        DealStage.pipeline => 'Pipeline',
        DealStage.underReview => 'Under review',
        DealStage.summitReady => 'Summit-ready',
        DealStage.dealRoom => 'Deal room',
        DealStage.committed => 'Committed',
      };

  /// True from SUMMIT_READY onward — feeds the "Summit-ready" StatTile.
  bool get isSummitReadyPlus => index >= DealStage.summitReady.index;

  /// Bucket a backend lifecycle status. Unknown/missing statuses fall back to
  /// the mid-funnel [DealStage.pipeline] bucket so new server statuses never
  /// crash the list.
  static DealStage fromStatus(String? raw) => switch (raw) {
        'INCUBATION' => DealStage.incubation,
        'DRAFT' || 'PIPELINE' || 'ON_HOLD' => DealStage.pipeline,
        'UNDER_REVIEW' || 'NEEDS_REVISION' || 'DECLINED' => DealStage.underReview,
        'SUMMIT_READY' => DealStage.summitReady,
        'DEAL_ROOM_FEATURED' || 'IN_NEGOTIATION' => DealStage.dealRoom,
        'COMMITTED' || 'IMPLEMENTED' => DealStage.committed,
        _ => DealStage.pipeline,
      };
}

/// One TWG project as the member sees it (ProjectMemberRead).
class DealProject {
  const DealProject({
    required this.id,
    required this.name,
    required this.sector,
    required this.stage,
    required this.value,
    required this.readinessScore,
    required this.afcenScore,
    required this.strategicScore,
    required this.location,
    required this.description,
    required this.isFollowing,
    required this.interestCount,
  });

  final String id;
  final String name;
  final String? sector; // Project.pillar, e.g. "energy_infrastructure"
  final DealStage stage;
  final double? value; // investment_size — Decimal serialized as a JSON string
  final double? readinessScore;
  final double? afcenScore; // WAIIS 0-100
  final double? strategicScore;
  final String? location;
  final String? description;
  final bool isFollowing;
  final int interestCount;

  String get stageLabel => stage.label;
  bool get isSummitReadyPlus => stage.isSummitReadyPlus;

  /// Copy with new interest state (optimistic Follow toggle + reconcile).
  DealProject copyWith({bool? isFollowing, int? interestCount}) => DealProject(
        id: id,
        name: name,
        sector: sector,
        stage: stage,
        value: value,
        readinessScore: readinessScore,
        afcenScore: afcenScore,
        strategicScore: strategicScore,
        location: location,
        description: description,
        isFollowing: isFollowing ?? this.isFollowing,
        interestCount: interestCount ?? this.interestCount,
      );

  factory DealProject.fromJson(Map<String, dynamic> j) => DealProject(
        id: j['id'].toString(),
        name: (j['name'] ?? '').toString(),
        sector: j['sector']?.toString(),
        stage: DealStageX.fromStatus(j['status']?.toString()),
        value: _toDouble(j['investment_size']),
        readinessScore: _toDouble(j['readiness_score']),
        afcenScore: _toDouble(j['afcen_score']),
        strategicScore: _toDouble(j['strategic_alignment_score']),
        location: j['location']?.toString(),
        description: j['description']?.toString(),
        isFollowing: (j['is_following'] as bool?) ?? false,
        interestCount: (j['interest_count'] as num?)?.toInt() ?? 0,
      );
}

/// Authoritative follow state returned by POST/DELETE …/interest — used to
/// reconcile the optimistic UI with the server's count.
class DealInterestState {
  const DealInterestState({
    required this.projectId,
    required this.isFollowing,
    required this.interestCount,
  });

  final String projectId;
  final bool isFollowing;
  final int interestCount;

  factory DealInterestState.fromJson(Map<String, dynamic> j) => DealInterestState(
        projectId: j['project_id'].toString(),
        isFollowing: (j['is_following'] as bool?) ?? false,
        interestCount: (j['interest_count'] as num?)?.toInt() ?? 0,
      );
}

/// Tolerant numeric parse: backend sends Decimals as JSON strings
/// ("25000000.00") and scores as JSON numbers; anything else -> null.
double? _toDouble(Object? v) => switch (v) {
      null => null,
      final num n => n.toDouble(),
      final String s => double.tryParse(s),
      _ => null,
    };
