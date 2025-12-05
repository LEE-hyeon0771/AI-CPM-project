import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:http/http.dart' as http;

class CpmHomePage extends StatefulWidget {
  const CpmHomePage({super.key});

  @override
  State<CpmHomePage> createState() => _CpmHomePageState();
}

class _CpmHomePageState extends State<CpmHomePage> {
  // 사용자가 직접 입력하도록 기본값은 비워두고, hintText로 예시만 제공
  final TextEditingController _messageController = TextEditingController();
  final TextEditingController _wbsController = TextEditingController();

  bool _loading = false;
  Map<String, dynamic>? _response;
  String? _error;

  // 마지막 분석에 사용된 질문 / WBS를 별도로 보관해서
  // 입력창은 비우고 아래쪽 박스로만 보여준다.
  String? _lastMessage;
  String? _lastWbs;

  // 각 카드별 subtitle 스트리밍 텍스트와 타이머
  List<String> _streamingCardTexts = [];
  List<Timer?> _cardTimers = [];

  // 각 테이블별로 현재까지 보여줄 행(row) 개수와 타이머
  List<int> _tableVisibleRowCounts = [];
  List<Timer?> _tableTimers = [];

  //static const String _backendBaseUrl = 'http://127.0.0.1:8000';
  static const String _backendBaseUrl = 'http://192.168.0.2:8000'; // ← PC IP로 변경

  @override
  void dispose() {
    _messageController.dispose();
    _wbsController.dispose();
    for (final t in _cardTimers) {
      t?.cancel();
    }
    for (final t in _tableTimers) {
      t?.cancel();
    }
    super.dispose();
  }

  Future<void> _runAnalysis() async {
    // 현재 입력값을 별도 변수에 보관 (이후 컨트롤러는 비울 예정)
    final message = _messageController.text.trim();
    final wbsText = _wbsController.text.trim();

    if (!mounted) return;
    setState(() {
      _loading = true;
      _error = null;
      _lastMessage = message.isEmpty ? null : message;
      _lastWbs = wbsText.isEmpty ? null : wbsText;
    });

    // 이전 스트리밍 상태 초기화
    for (final t in _cardTimers) {
      t?.cancel();
    }
    _cardTimers = [];
    _streamingCardTexts = [];

    for (final t in _tableTimers) {
      t?.cancel();
    }
    _tableTimers = [];
    _tableVisibleRowCounts = [];

    try {
      final res = await http.post(
        Uri.parse('$_backendBaseUrl/api/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'message': message,
          'wbs_text': wbsText.isEmpty ? null : wbsText,
        }),
      );

      if (!mounted) return;

      if (res.statusCode >= 200 && res.statusCode < 300) {
        setState(() {
          _response = jsonDecode(res.body) as Map<String, dynamic>;
          // 성공적으로 분석이 끝나면 입력창은 비워서 다음 입력을 위한 상태로 둔다.
          _messageController.clear();
          _wbsController.clear();
        });

        // 모든 카드의 subtitle을 동시에 스트리밍 형태로 보여줌
        final ui = _response?['ui'] as Map<String, dynamic>? ?? {};
        final cards = (ui['cards'] as List?) ?? [];
        _startStreamingForCards(cards);

        // 테이블(이상 일정, 날씨 반영 일정표, 지연 분석)의 행도 순차적으로 스트리밍
        final tables = (ui['tables'] as List?) ?? [];
        _startStreamingForTables(tables);
      } else {
        setState(() {
          _error = 'HTTP ${res.statusCode}: ${res.body}';
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
      });
    } finally {
      if (!mounted) return;
      setState(() {
        _loading = false;
      });
    }
  }

  void _startStreamingForCards(List<dynamic> cards) {
    // 카드 개수만큼 스트리밍 버퍼와 타이머 초기화
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
            // 스트리밍이 끝나면 버퍼를 비워서 원본 subtitle이 보이도록
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

  void _startStreamingForTables(List<dynamic> tables) {
    _tableTimers = List<Timer?>.filled(tables.length, null, growable: true);
    _tableVisibleRowCounts =
        List<int>.filled(tables.length, 0, growable: true);

    const interval = Duration(milliseconds: 80); // 행 단위이므로 조금 느리게

    for (int i = 0; i < tables.length; i++) {
      final table = tables[i] as Map<String, dynamic>;
      final rows = (table['rows'] as List?) ?? [];
      if (rows.isEmpty) continue;

      _tableTimers[i] = Timer.periodic(interval, (timer) {
        if (!mounted) {
          timer.cancel();
          return;
        }

        final totalRows = rows.length;
        final current = _tableVisibleRowCounts[i];

        if (current >= totalRows) {
          timer.cancel();
          return;
        }

        setState(() {
          _tableVisibleRowCounts[i] = current + 1;
        });
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('스마트 건설 일정 분석'),
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
                          '입력',
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
                                controller: _messageController,
                                decoration: const InputDecoration(
                                  labelText: '메시지',
                                  hintText:
                                      '예) 아래 공사 WBS를 가지고 이상적인 공정표를 CPM으로 짜주고, 예상되는 날씨/공휴일 지연까지 같이 분석해줘.',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                              const SizedBox(height: 12),
                              TextField(
                                controller: _wbsController,
                                decoration: const InputDecoration(
                                  labelText: 'WBS (자연어로 자유롭게 작성 가능)',
                                  hintText:
                                      '예) 기초 토공 굴착을 5일 동안 하고, 바로 이어서 기초 콘크리트를 3일, 그 다음 구조 골조 타설을 10일, 마지막으로 마감 공사를 7일 진행한다고 가정하자...',
                                  border: OutlineInputBorder(),
                                ),
                                maxLines: 4,
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
                                  onPressed: _loading ? null : _runAnalysis,
                                  child: _loading
                                      ? const SizedBox(
                                          width: 18,
                                          height: 18,
                                          child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: Colors.white),
                                        )
                                      : const Text('분석 실행'),
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
                          _buildResults(),
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

  /// 마지막 분석에 사용된 질문 / WBS를 요약해서 보여주는 박스
  Widget _buildQuerySummaryBox() {
    final hasMessage =
        _lastMessage != null && _lastMessage!.trim().isNotEmpty;
    final hasWbs = _lastWbs != null && _lastWbs!.trim().isNotEmpty;

    if (!hasMessage && !hasWbs) {
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
            '이번 분석에 사용된 입력',
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Color(0xFF6366F1),
            ),
          ),
          const SizedBox(height: 8),
          if (hasMessage) ...[
            const Text(
              '질문',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Color(0xFF4B5563),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _lastMessage!,
              style: const TextStyle(fontSize: 12, color: Color(0xFF111827)),
            ),
          ],
          if (hasMessage && hasWbs) const SizedBox(height: 8),
          if (hasWbs) ...[
            const Text(
              'WBS',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: Color(0xFF4B5563),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _lastWbs!,
              style: const TextStyle(fontSize: 12, color: Color(0xFF111827)),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildResults() {
    final ui = _response?['ui'] as Map<String, dynamic>? ?? {};
    final tables = (ui['tables'] as List?) ?? [];
    final cards = (ui['cards'] as List?) ?? [];

    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (cards.isNotEmpty) ...[
            const Text(
              '요약 카드',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (int i = 0; i < cards.length; i++)
                  _buildSummaryCard(cards[i] as Map<String, dynamic>, i),
              ],
            ),
            const SizedBox(height: 16),
          ],
          if (tables.isNotEmpty) ...[
            const Text(
              '테이블',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            for (int i = 0; i < tables.length; i++)
              _buildTableCard(tables[i] as Map<String, dynamic>, i),
          ],
        ],
      ),
    );
  }

  Widget _buildTableCard(Map<String, dynamic> table, int tableIndex) {
    final headers = (table['headers'] as List).cast<String>();
    final rows = (table['rows'] as List).cast<List>();

    int visibleCount = rows.length;
    if (_tableVisibleRowCounts.length > tableIndex &&
        _tableVisibleRowCounts[tableIndex] > 0) {
      visibleCount =
          _tableVisibleRowCounts[tableIndex].clamp(0, rows.length);
    }
    final visibleRows = rows.take(visibleCount).toList();

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
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                ],
                rows: [
                  for (final r in visibleRows)
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

  Widget _buildSummaryCard(Map<String, dynamic> card, int cardIndex) {
    final title = card['title']?.toString() ?? '';
    final value = card['value']?.toString() ?? '';

    // 해당 카드 인덱스에 대한 스트리밍 텍스트가 있으면 그것을 사용하고,
    // 없으면 원래 subtitle을 사용
    final originalSubtitle = card['subtitle']?.toString() ?? '';
    String subtitle = originalSubtitle;
    if (_streamingCardTexts.length > cardIndex &&
        _streamingCardTexts[cardIndex].isNotEmpty) {
      subtitle = _streamingCardTexts[cardIndex];
    }

    return SizedBox(
      width: 260,
      child: Card(
        elevation: 2,
        child: Padding(
          padding: const EdgeInsets.all(12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                    fontSize: 14, fontWeight: FontWeight.bold),
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
      ),
    );
  }
}