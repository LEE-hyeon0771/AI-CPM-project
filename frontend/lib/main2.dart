import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

void main() {
  runApp(const LawQaApp());
}

class LawQaApp extends StatelessWidget {
  const LawQaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Safety Regulation Q&A',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF6366F1)),
        useMaterial3: true,
        textTheme: GoogleFonts.notoSansKrTextTheme(),
      ),
      home: const LawQaPage(),
    );
  }
}

class LawQaPage extends StatefulWidget {
  const LawQaPage({super.key});

  @override
  State<LawQaPage> createState() => _LawQaPageState();
}

class _LawQaPageState extends State<LawQaPage> {
  final TextEditingController _questionController = TextEditingController();

  bool _loading = false;
  Map<String, dynamic>? _response;
  String? _error;

  // 마지막 분석에 사용된 질문을 별도로 보관해서
  // 입력창은 비우고 아래쪽 박스로만 보여준다.
  String? _lastQuestion;

  // 카드별 subtitle 스트리밍용
  List<String> _streamingCardTexts = [];
  List<Timer?> _cardTimers = [];

  //static const String _backendBaseUrl = 'http://127.0.0.1:8000';
  static const String _backendBaseUrl = 'http://192.168.0.2:8000'; // ← PC IP로 변경
  @override
  void dispose() {
    _questionController.dispose();
    for (final t in _cardTimers) {
      t?.cancel();
    }
    super.dispose();
  }

  Future<void> _askLawQuestion() async {
    final question = _questionController.text.trim();

    setState(() {
      _loading = true;
      _error = null;
      _lastQuestion = question.isEmpty ? null : question;
    });

    // 스트리밍 상태 초기화
    for (final t in _cardTimers) {
      t?.cancel();
    }
    _cardTimers = [];
    _streamingCardTexts = [];

    try {
      final res = await http.post(
        Uri.parse('$_backendBaseUrl/api/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': question,
          'wbs_text': null, // 법규 전용 화면이므로 WBS는 항상 비움
          'mode': 'law_only', // 백엔드에 법규 전용 모드임을 명시
        }),
      );

      if (res.statusCode >= 200 && res.statusCode < 300) {
        setState(() {
          _response = jsonDecode(res.body) as Map<String, dynamic>;
          // 성공적으로 분석이 끝나면 입력창을 비워서 다음 질문 입력을 편하게
          _questionController.clear();
        });

        final ui = _response?['ui'] as Map<String, dynamic>? ?? {};
        final cards = (ui['cards'] as List?) ?? [];
        _startStreamingForCards(cards);
      } else {
        setState(() {
          _error = 'HTTP ${res.statusCode}: ${res.body}';
        });
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  void _startStreamingForCards(List<dynamic> cards) {
    _cardTimers = List<Timer?>.filled(cards.length, null, growable: true);
    _streamingCardTexts =
        List<String>.filled(cards.length, '', growable: true);

    const interval = Duration(milliseconds: 20);

    for (int i = 0; i < cards.length; i++) {
      final card = cards[i] as Map<String, dynamic>;
      final subtitle = card['subtitle']?.toString() ?? '';
      if (subtitle.isEmpty) continue;

      int index = 0;
      _cardTimers[i] = Timer.periodic(interval, (timer) {
        if (!mounted) {
          timer.cancel();
          return;
        }

        if (index >= subtitle.length) {
          timer.cancel();
          setState(() {
            _streamingCardTexts[i] = '';
          });
          return;
        }

        setState(() {
          _streamingCardTexts[i] = subtitle.substring(0, index + 1);
        });
        index++;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('건설 안전 규정 Q&A'),
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: Navigator.canPop(context)
            ? IconButton(
                icon: const Icon(Icons.arrow_back, color: Color(0xFF6366F1)),
                onPressed: () => Navigator.of(context).pop(),
              )
            : null,
      ),
      extendBodyBehindAppBar: true,
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              Color(0xFFF5F3FF),
              Color(0xFFE0F2FE),
            ],
          ),
        ),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              return SingleChildScrollView(
                child: ConstrainedBox(
                  constraints: BoxConstraints(minHeight: constraints.maxHeight),
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const Text(
                          '법규 질의',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF6366F1),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.black.withOpacity(0.03),
                                blurRadius: 8,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            children: [
                              TextField(
                                controller: _questionController,
                                decoration: const InputDecoration(
                                  labelText: '질문',
                                  hintText:
                                      '예) 기초 콘크리트 타설과 구조 골조 타설 시 강풍·저온·강우에 따른 작업 중지 기준을 알려줘.',
                                  border: OutlineInputBorder(),
                                ),
                                maxLines: 3,
                              ),
                              const SizedBox(height: 12),
                              SizedBox(
                                width: double.infinity,
                                child: ElevatedButton(
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF6366F1),
                                    foregroundColor: Colors.white,
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                  ),
                                  onPressed:
                                      _loading ? null : _askLawQuestion,
                                  child: _loading
                                      ? const SizedBox(
                                          width: 18,
                                          height: 18,
                                          child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white),
                                        )
                                      : const Text('규정 분석 요청'),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                        if (_error != null)
                          Text(
                            'Error: $_error',
                            style: const TextStyle(color: Colors.red),
                          ),
                        if (_response != null) ...[
                          const SizedBox(height: 12),
                          _buildQuerySummaryBox(),
                          const SizedBox(height: 12),
                          _buildLawResults(),
                        ],
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  /// 마지막 분석에 사용된 질문을 요약해서 보여주는 박스
  Widget _buildQuerySummaryBox() {
    final hasQuestion =
        _lastQuestion != null && _lastQuestion!.trim().isNotEmpty;

    if (!hasQuestion) {
      return const SizedBox.shrink();
    }

    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '이번 분석에 사용된 질문',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Color(0xFF6366F1),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _lastQuestion!,
            style: const TextStyle(fontSize: 12, color: Color(0xFF111827)),
          ),
        ],
      ),
    );
  }

  Widget _buildLawResults() {
    final ui = _response?['ui'] as Map<String, dynamic>? ?? {};
    final tables = (ui['tables'] as List?) ?? [];
    final allCards = (ui['cards'] as List?) ?? [];
    final citations = (_response?['citations'] as List?) ?? [];

    // 법규 전용 화면에서는 "💡 법규 설명" 카드만 사용
    final cards = allCards
        .where((c) =>
            ((c as Map<String, dynamic>)['title']?.toString() ?? '')
                .contains('법규 설명'))
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (cards.isNotEmpty) ...[
          const Text(
            '요약 카드',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (int i = 0; i < cards.length; i++)
                _buildCard(cards[i] as Map<String, dynamic>, i),
            ],
          ),
          const SizedBox(height: 16),
        ],
        if (citations.isNotEmpty) ...[
          const Text(
            '참고 문서',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          _buildCitationsList(citations),
          const SizedBox(height: 16),
        ],
        if (tables.isNotEmpty) ...[
          const Text(
            '테이블',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          for (final t in tables) _buildTableCard(t as Map<String, dynamic>),
        ],
      ],
    );
  }

  Widget _buildCard(Map<String, dynamic> card, int index) {
    final title = card['title']?.toString() ?? '';
    final value = card['value']?.toString() ?? '';

    final originalSubtitle = card['subtitle']?.toString() ?? '';
    String subtitle = originalSubtitle;
    if (_streamingCardTexts.length > index &&
        _streamingCardTexts[index].isNotEmpty) {
      subtitle = _streamingCardTexts[index];
    }

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style:
                    const TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 4),
              Text(
                value,
                style: const TextStyle(
                    fontSize: 20, fontWeight: FontWeight.w600),
              ),
              if (subtitle.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 12),
                 ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCitationsList(List<dynamic> citations) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (int i = 0; i < citations.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: _buildCitationItem(citations[i] as Map<String, dynamic>, i),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCitationItem(Map<String, dynamic> c, int index) {
    final doc = c['document']?.toString() ?? '';
    final page = c['page']?.toString() ?? '';
    final snippet = c['snippet']?.toString() ?? '';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          '[${index + 1}] $doc (p.$page)',
          style: const TextStyle(
              fontWeight: FontWeight.bold, fontSize: 13),
        ),
        const SizedBox(height: 2),
        Text(
          snippet,
          style: const TextStyle(fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildTableCard(Map<String, dynamic> table) {
    final headers = (table['headers'] as List).cast<String>();
    final rows = (table['rows'] as List).cast<List>();

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              table['title']?.toString() ?? '',
              style:
                  const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: [
                  for (final h in headers)
                    DataColumn(
                      label: Text(
                        h,
                        style:
                            const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                ],
                rows: [
                  for (final r in rows)
                    DataRow(
                      cells: [
                        for (final cell in r)
                          DataCell(Text(cell.toString())),
                      ],
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}


