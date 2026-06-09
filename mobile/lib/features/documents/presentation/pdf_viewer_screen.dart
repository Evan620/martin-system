// lib/features/documents/presentation/pdf_viewer_screen.dart
//
// In-app PDF viewer. Fetches the document bytes via the documents repository
// (JWT bearer applied by the shared Dio interceptor) and renders them with
// `pdfx` (pinch-to-zoom). Reached as a nested route in the Documents branch of
// the StatefulShellRoute, so the floating nav persists.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pdfx/pdfx.dart';

import '../../../core/theme/sovereign_colors.dart';
import '../application/documents_controller.dart';
import '../data/documents_repository.dart';

class PdfViewerScreen extends ConsumerStatefulWidget {
  const PdfViewerScreen({super.key, required this.documentId, required this.title});

  final String documentId;
  final String title;

  @override
  ConsumerState<PdfViewerScreen> createState() => _PdfViewerScreenState();
}

class _PdfViewerScreenState extends ConsumerState<PdfViewerScreen> {
  PdfControllerPinch? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _open();
  }

  Future<void> _open() async {
    try {
      final bytes = await ref.read(documentsRepositoryProvider).downloadBytes(widget.documentId);
      if (!mounted) return;
      setState(() => _controller = PdfControllerPinch(document: PdfDocument.openData(bytes)));
    } on DocumentException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SovereignColors.navyDeep,
      appBar: AppBar(
        backgroundColor: SovereignColors.navy,
        foregroundColor: SovereignColors.ivory,
        title: Text(widget.title, style: const TextStyle(fontSize: 15)),
      ),
      body: _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: SovereignColors.ivory.withValues(alpha: 0.85)),
                ),
              ),
            )
          : _controller == null
              ? const Center(child: CircularProgressIndicator(color: SovereignColors.gold))
              : PdfViewPinch(controller: _controller!),
    );
  }
}
