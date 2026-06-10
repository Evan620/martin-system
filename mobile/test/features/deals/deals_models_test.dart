// test/features/deals/deals_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/deals/data/deals_models.dart';

void main() {
  group('DealStage', () {
    test('buckets every backend status per the spec', () {
      expect(DealStageX.fromStatus('INCUBATION'), DealStage.incubation);
      expect(DealStageX.fromStatus('DRAFT'), DealStage.pipeline);
      expect(DealStageX.fromStatus('PIPELINE'), DealStage.pipeline);
      expect(DealStageX.fromStatus('ON_HOLD'), DealStage.pipeline);
      expect(DealStageX.fromStatus('UNDER_REVIEW'), DealStage.underReview);
      expect(DealStageX.fromStatus('NEEDS_REVISION'), DealStage.underReview);
      expect(DealStageX.fromStatus('DECLINED'), DealStage.underReview);
      expect(DealStageX.fromStatus('SUMMIT_READY'), DealStage.summitReady);
      expect(DealStageX.fromStatus('DEAL_ROOM_FEATURED'), DealStage.dealRoom);
      expect(DealStageX.fromStatus('IN_NEGOTIATION'), DealStage.dealRoom);
      expect(DealStageX.fromStatus('COMMITTED'), DealStage.committed);
      expect(DealStageX.fromStatus('IMPLEMENTED'), DealStage.committed);
    });

    test('unknown or missing status falls back to the pipeline bucket', () {
      expect(DealStageX.fromStatus('SOMETHING_NEW'), DealStage.pipeline);
      expect(DealStageX.fromStatus(null), DealStage.pipeline);
      expect(DealStageX.fromStatus(''), DealStage.pipeline);
    });

    test('member-friendly labels', () {
      expect(DealStage.incubation.label, 'Incubation');
      expect(DealStage.pipeline.label, 'Pipeline');
      expect(DealStage.underReview.label, 'Under review');
      expect(DealStage.summitReady.label, 'Summit-ready');
      expect(DealStage.dealRoom.label, 'Deal room');
      expect(DealStage.committed.label, 'Committed');
    });

    test('isSummitReadyPlus flips at SUMMIT_READY', () {
      expect(DealStage.incubation.isSummitReadyPlus, isFalse);
      expect(DealStage.pipeline.isSummitReadyPlus, isFalse);
      expect(DealStage.underReview.isSummitReadyPlus, isFalse);
      expect(DealStage.summitReady.isSummitReadyPlus, isTrue);
      expect(DealStage.dealRoom.isSummitReadyPlus, isTrue);
      expect(DealStage.committed.isSummitReadyPlus, isTrue);
    });
  });

  group('DealProject.fromJson', () {
    test('parses the full ProjectMemberRead contract', () {
      final p = DealProject.fromJson({
        'id': 'a1b2',
        'name': 'Bagre Solar PV',
        'sector': 'energy_infrastructure',
        'status': 'SUMMIT_READY',
        'investment_size': '25000000.00', // Decimal serialized as STRING
        'currency': 'USD',
        'readiness_score': 4.2,
        'afcen_score': 55.0,
        'strategic_alignment_score': null,
        'location': 'Ghana',
        'description': 'A 50MW solar plant.',
        'is_following': true,
        'interest_count': 3,
      });
      expect(p.id, 'a1b2');
      expect(p.name, 'Bagre Solar PV');
      expect(p.sector, 'energy_infrastructure');
      expect(p.stage, DealStage.summitReady);
      expect(p.stageLabel, 'Summit-ready');
      expect(p.value, 25000000.0);
      expect(p.readinessScore, 4.2);
      expect(p.afcenScore, 55.0);
      expect(p.strategicScore, isNull);
      expect(p.location, 'Ghana');
      expect(p.description, 'A 50MW solar plant.');
      expect(p.isFollowing, isTrue);
      expect(p.interestCount, 3);
      expect(p.isSummitReadyPlus, isTrue);
    });

    test('tolerates nulls and missing optionals', () {
      final p = DealProject.fromJson({
        'id': 'x1',
        'name': 'Minimal',
        'status': 'INCUBATION',
      });
      expect(p.sector, isNull);
      expect(p.value, isNull);
      expect(p.readinessScore, isNull);
      expect(p.afcenScore, isNull);
      expect(p.strategicScore, isNull);
      expect(p.location, isNull);
      expect(p.description, isNull);
      expect(p.isFollowing, isFalse);
      expect(p.interestCount, 0);
      expect(p.stage, DealStage.incubation);
    });

    test('unknown status buckets to the fallback stage', () {
      final p = DealProject.fromJson({
        'id': 'x2',
        'name': 'Odd',
        'status': 'FUTURE_STATUS_WE_DONT_KNOW',
      });
      expect(p.stage, DealStage.pipeline);
      expect(p.stageLabel, 'Pipeline');
    });

    test('value parses from number too, unparseable string -> null', () {
      expect(
        DealProject.fromJson({'id': '1', 'name': 'N', 'status': 'DRAFT', 'investment_size': 5000000})
            .value,
        5000000.0,
      );
      expect(
        DealProject.fromJson({'id': '1', 'name': 'N', 'status': 'DRAFT', 'investment_size': 'TBD'})
            .value,
        isNull,
      );
    });

    test('copyWith flips only the interest fields', () {
      final p = DealProject.fromJson({
        'id': 'c1', 'name': 'Copy', 'status': 'PIPELINE',
        'is_following': false, 'interest_count': 1,
      });
      final q = p.copyWith(isFollowing: true, interestCount: 2);
      expect(q.isFollowing, isTrue);
      expect(q.interestCount, 2);
      expect(q.id, p.id);
      expect(q.name, p.name);
      expect(q.stage, p.stage);
    });
  });

  test('DealInterestState.fromJson parses the reconcile payload', () {
    final s = DealInterestState.fromJson({
      'project_id': 'a1b2',
      'is_following': true,
      'interest_count': 4,
    });
    expect(s.projectId, 'a1b2');
    expect(s.isFollowing, isTrue);
    expect(s.interestCount, 4);
  });
}
