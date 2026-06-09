// test/routing/sovereign_page_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:member_app/routing/sovereign_page.dart';

void main() {
  test('sovereignPage returns a CustomTransitionPage with the child + 280ms', () {
    const child = Text('x');
    final page = sovereignPage<void>(child: child);
    expect(page, isA<CustomTransitionPage<void>>());
    expect(page.child, same(child));
    expect(page.transitionDuration, const Duration(milliseconds: 280));
  });
}
