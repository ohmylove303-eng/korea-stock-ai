"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Modal, Group, Stack, Text, Badge, Loader, Center, Grid, Divider, Button, Alert, Paper, Progress, SegmentedControl, ThemeIcon, Anchor } from "@mantine/core";
import { IconReload, IconShieldCheck, IconSword, IconInfoCircle, IconRobot, IconNews } from "@tabler/icons-react";
import { fetchStockAnalysis, fetchStockHistory, Signal, StockHistory } from "@/lib/api";
import { NiceRadarChart } from "./NiceRadarChart";
import { createChart, CandlestickSeries, HistogramSeries, ColorType, CrosshairMode } from "lightweight-charts";
import type { IChartApi, ISeriesApi, CandlestickData, HistogramData, Time } from "lightweight-charts";

interface StockChartModalProps {
    opened: boolean;
    onClose: () => void;
    signal: Signal | null;
}

/**
 * Lightweight Charts Candlestick + Volume chart component.
 * Uses pykrx OHLCV data from our own backend.
 */
function OHLCVChart({ ticker, period = '1y' }: { ticker: string; period?: string }) {
    const containerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        // Cleanup previous chart
        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
        }

        const chart = createChart(containerRef.current, {
            width: containerRef.current.clientWidth,
            height: 460,
            layout: {
                background: { type: ColorType.Solid, color: '#131722' },
                textColor: '#d1d4dc',
                fontSize: 12,
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            crosshair: {
                mode: CrosshairMode.Normal,
            },
            rightPriceScale: {
                borderColor: 'rgba(197, 203, 206, 0.2)',
            },
            timeScale: {
                borderColor: 'rgba(197, 203, 206, 0.2)',
                timeVisible: false,
            },
        });

        chartRef.current = chart;

        // Candlestick series (Korean style: red = up, blue = down)
        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#ef5350',
            downColor: '#2196f3',
            borderVisible: false,
            wickUpColor: '#ef5350',
            wickDownColor: '#2196f3',
        });

        // Volume histogram overlay
        const volumeSeries = chart.addSeries(HistogramSeries, {
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });
        volumeSeries.priceScale().applyOptions({
            scaleMargins: { top: 0.8, bottom: 0 },
        });

        // Fetch data
        setLoading(true);
        setError(null);

        fetchStockHistory(ticker)
            .then((data: StockHistory[]) => {
                if (!data || data.length === 0) {
                    setError('차트 데이터가 없습니다.');
                    setLoading(false);
                    return;
                }

                const candles: CandlestickData<Time>[] = data.map(d => ({
                    time: d.date as Time,
                    open: d.open,
                    high: d.high,
                    low: d.low,
                    close: d.close,
                }));

                const volumes: HistogramData<Time>[] = data.map(d => ({
                    time: d.date as Time,
                    value: d.volume,
                    color: d.close >= d.open
                        ? 'rgba(239, 83, 80, 0.3)'
                        : 'rgba(33, 150, 243, 0.3)',
                }));

                candleSeries.setData(candles);
                volumeSeries.setData(volumes);
                chart.timeScale().fitContent();
                setLoading(false);
            })
            .catch(err => {
                console.error('Chart data error:', err);
                setError('차트 로딩 실패');
                setLoading(false);
            });

        // Resize observer
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                const { width } = entry.contentRect;
                if (width > 0) {
                    chart.applyOptions({ width });
                }
            }
        });
        resizeObserver.observe(containerRef.current);

        return () => {
            resizeObserver.disconnect();
            chart.remove();
            chartRef.current = null;
        };
    }, [ticker, period]);

    return (
        <div style={{ position: 'relative' }}>
            <div
                ref={containerRef}
                style={{
                    width: '100%',
                    height: 460,
                    borderRadius: 8,
                    overflow: 'hidden',
                    border: '1px solid rgba(255,255,255,0.1)',
                }}
            />
            {loading && (
                <Center style={{
                    position: 'absolute',
                    top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(19, 23, 34, 0.8)',
                    borderRadius: 8,
                }}>
                    <Stack align="center" gap="xs">
                        <Loader color="blue" size="md" />
                        <Text size="xs" c="dimmed">차트 로딩중...</Text>
                    </Stack>
                </Center>
            )}
            {error && (
                <Center style={{
                    position: 'absolute',
                    top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(19, 23, 34, 0.9)',
                    borderRadius: 8,
                }}>
                    <Text size="sm" c="red">{error}</Text>
                </Center>
            )}
        </div>
    );
}

export function StockChartModal({ opened, onClose, signal: initialSignal }: StockChartModalProps) {
    const [analyzing, setAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [signal, setSignal] = useState<Signal | null>(initialSignal);
    const [analysisResult, setAnalysisResult] = useState<{ source: string; action: string; reason: string } | null>(null);
    const [chartPeriod, setChartPeriod] = useState('1y');

    // Sync prop to state when modal opens
    useEffect(() => {
        setSignal(initialSignal);
        setAnalysisResult(null);
        setError(null);
    }, [initialSignal, opened]);

    const handleReAnalyze = async () => {
        if (!signal) return;
        try {
            setAnalyzing(true);
            setAnalysisResult(null);

            const freshSignal = await fetchStockAnalysis(signal.ticker);
            setSignal(prev => prev ? ({ ...prev, ...freshSignal }) : freshSignal);

            const rec = freshSignal.gpt_recommendation;
            const source = (rec as any)?.source || 'AI Model';

            setAnalysisResult({
                source: source,
                action: rec?.action || 'HOLD',
                reason: rec?.reason || 'Analysis completed.'
            });

        } catch (e) {
            console.error(e);
            setError("분석 실패. 다시 시도해 주세요.");
        } finally {
            setAnalyzing(false);
        }
    };

    if (!signal) return null;

    // Prepare NICE Radar Data
    const layers = signal.nice_layers || (signal as any);
    const L1 = layers?.L1_technical ?? 0;
    const L2 = layers?.L2_supply ?? 0;
    const L3 = layers?.L3_sentiment ?? 0;
    const L4 = layers?.L4_macro ?? 0;
    const L5 = layers?.L5_institutional ?? 0;
    const aiVerified = layers?.ai_verified !== false; // Default to true if undefined for backward compat

    const radarData = [
        { subject: 'Technical', A: L1, fullMark: 100 },
        { subject: 'Supply', A: L2, fullMark: 100 },
        { subject: 'Sentiment', A: L3, fullMark: 100 },
        { subject: 'Macro', A: L4, fullMark: 100 },
        { subject: 'Inst.', A: L5, fullMark: 100 },
    ];

    const totalScore = layers?.total ?? 0;
    const niceScore = Math.round(totalScore);

    const niceDetails = [
        { label: 'L1 기술', value: L1, max: 100, color: 'blue' },
        { label: 'L2 공급', value: L2, max: 100, color: 'teal' },
        { label: 'L3 감정 (AI)', value: L3, max: 100, color: 'yellow' },
        { label: 'L4 매크로', value: L4, max: 100, color: 'orange' },
        { label: 'L5 기관', value: L5, max: 100, color: 'grape' },
    ];

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title={
                <Group>
                    <Text fw={700} size="lg">{signal.name}</Text>
                    <Text size="sm" c="dimmed">{signal.ticker}</Text>
                    <Badge color={(signal.return_pct ?? 0) >= 0 ? "red" : "blue"} variant="light" size="lg">
                        {(signal.return_pct ?? 0) > 0 ? "+" : ""}{(signal.return_pct ?? 0).toFixed(2)}%
                    </Badge>
                    {signal.is_palantir && <Badge color="grape" leftSection={<IconShieldCheck size={12} />}>PALANTIR</Badge>}
                    {signal.is_palantir_mini && <Badge color="orange" leftSection={<IconSword size={12} />}>MINI</Badge>}
                </Group>
            }
            size="90rem"
            centered
            styles={{
                content: { backgroundColor: '#1A1A1A', border: '1px solid rgba(255,255,255,0.1)' },
                header: { backgroundColor: '#1A1A1A', color: 'white' },
                body: { backgroundColor: '#1A1A1A', color: 'white' }
            }}
        >
            <Grid gutter="xl">
                {/* Left: Chart + AI */}
                <Grid.Col span={{ base: 12, md: 8 }}>
                    <Stack>
                        {/* Period selector */}
                        <Group justify="flex-end">
                            <SegmentedControl
                                size="xs"
                                value={chartPeriod}
                                onChange={setChartPeriod}
                                data={[
                                    { label: '3개월', value: '3m' },
                                    { label: '6개월', value: '6m' },
                                    { label: '1년', value: '1y' },
                                ]}
                                styles={{
                                    root: { backgroundColor: 'rgba(255,255,255,0.05)' },
                                    label: { color: '#d1d4dc' },
                                }}
                            />
                        </Group>

                        {/* Lightweight Chart */}
                        {opened && (
                            <OHLCVChart ticker={signal.ticker} period={chartPeriod} />
                        )}

                        {error && <Text c="red" size="sm">{error}</Text>}

                        {analysisResult && (
                            <Stack>
                                <Alert
                                    icon={<IconRobot size={16} />}
                                    title={`AI 분석: ${analysisResult.action}`}
                                    color={analysisResult.action === 'BUY' ? 'teal' : analysisResult.action === 'SELL' ? 'red' : 'gray'}
                                    variant="light"
                                >
                                    <Text size="sm"><Text span fw={700}>[{analysisResult.source}]</Text> {analysisResult.reason}</Text>
                                </Alert>

                                {/* AI 분석 근거 및 뉴스 (투명성 강화) */}
                                {signal.news && signal.news.length > 0 && (
                                    <Paper withBorder p="sm" bg="rgba(0,0,0,0.2)">
                                        <Text size="xs" fw={700} c="dimmed" mb="xs">📚 분석 참고 자료 (AI 검색)</Text>
                                        <Stack gap="xs">
                                            {signal.news.map((news: any, idx: number) => (
                                                <Group key={`${idx}-${news.url || 'news'}`} gap="xs" wrap="nowrap" align="center">
                                                    <ThemeIcon size="xs" radius="xl" color="gray" variant="light" style={{ minWidth: 20 }}>
                                                        <IconNews size={10} />
                                                    </ThemeIcon>
                                                    <Text component="a" href={news.url} target="_blank" size="xs" c="blue" lineClamp={1} style={{ flex: 1 }}>
                                                        {news.title}
                                                    </Text>
                                                    <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
                                                        {news.date}
                                                    </Text>
                                                </Group>
                                            ))}
                                        </Stack>
                                    </Paper>
                                )}
                            </Stack>
                        )}

                        {/* Price & AI Controls */}
                        <Paper withBorder p="md" bg="rgba(255,255,255,0.05)" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                            <Group justify="space-between">
                                <Group>
                                    <Stack gap={0}>
                                        <Text size="xs" c="dimmed">현재가</Text>
                                        <Text fw={700} c="white">₩{(signal.current_price ?? 0).toLocaleString()}</Text>
                                    </Stack>
                                    <Divider orientation="vertical" />
                                    <Stack gap={0}>
                                        <Text size="xs" c="dimmed">TP1 / TP2</Text>
                                        <Group gap={4}>
                                            <Text fw={700} c="red">₩{(signal.tp1 || 0).toLocaleString()}</Text>
                                            <Text size="xs" c="dimmed">/</Text>
                                            <Text fw={700} c="red">₩{(signal.tp2 || 0).toLocaleString()}</Text>
                                        </Group>
                                    </Stack>
                                    <Divider orientation="vertical" />
                                    <Stack gap={0}>
                                        <Text size="xs" c="dimmed">GPT</Text>
                                        <Text fw={700} c="teal">{signal.gpt_recommendation?.action || "해당 사항 없음"}</Text>
                                    </Stack>
                                </Group>

                                <Button
                                    leftSection={analyzing ? <Loader size="xs" color="white" /> : <IconReload size={14} />}
                                    variant="light"
                                    color="blue"
                                    loading={analyzing}
                                    onClick={handleReAnalyze}
                                >
                                    {analyzing ? "분석중..." : "AI 재분석"}
                                </Button>
                            </Group>
                        </Paper>
                    </Stack>
                </Grid.Col>

                {/* Right: NICE Model Report */}
                <Grid.Col span={{ base: 12, md: 4 }}>
                    <Stack gap="lg" h="100%" justify="flex-start" pt="md">
                        <Stack gap={0} align="center">
                            <Group gap={6}>
                                <Text fw={700} size="sm" ta="center" c="dimmed" tt="uppercase">NICE 모델 분석</Text>
                                {!aiVerified && (
                                    <Badge color="orange" size="xs" variant="light" leftSection={<IconInfoCircle size={10} />}>
                                        AI 미검증
                                    </Badge>
                                )}
                            </Group>
                            <Text size="xs" c="dimmed">정량적 점수 시스템 (100점 만점)</Text>
                        </Stack>

                        {/* Radar Chart */}
                        <Center>
                            <NiceRadarChart data={radarData} score={niceScore} />
                        </Center>

                        <Divider color="white" opacity={0.1} />

                        {/* NICE Layer Breakdown */}
                        <Stack gap="xs">
                            <Text size="xs" c="dimmed" fw={700} tt="uppercase">레이어 분석</Text>
                            {niceDetails.map((d) => (
                                <Stack key={d.label} gap={2}>
                                    <Group justify="space-between">
                                        <Text size="xs" c="dimmed">{d.label}</Text>
                                        <Text size="xs" fw={700}>{d.value}/{d.max}</Text>
                                    </Group>
                                    <Progress value={(d.value / d.max) * 100} color={d.color} size="xs" radius="xl" />
                                </Stack>
                            ))}
                        </Stack>

                        <Divider color="white" opacity={0.1} />

                        {/* Detailed Metrics */}
                        <Stack gap="sm">
                            <Group justify="space-between">
                                <Group gap="xs">
                                    <IconInfoCircle size={14} color="gray" />
                                    <Text size="sm" c="dimmed">VCP 수축률</Text>
                                </Group>
                                <Text size="sm" fw={700}>{signal.contraction_ratio ? signal.contraction_ratio.toFixed(2) : '-'}</Text>
                            </Group>
                            <Group justify="space-between">
                                <Group gap="xs">
                                    <IconInfoCircle size={14} color="gray" />
                                    <Text size="sm" c="dimmed">외인 (5일)</Text>
                                </Group>
                                <Text size="sm" fw={700} c={(signal.foreign_5d || 0) > 0 ? "red" : "blue"}>
                                    {((signal.foreign_5d || 0) / 100000000).toFixed(1)}억
                                </Text>
                            </Group>
                            <Group justify="space-between">
                                <Group gap="xs">
                                    <IconInfoCircle size={14} color="gray" />
                                    <Text size="sm" c="dimmed">기관 (5일)</Text>
                                </Group>
                                <Text size="sm" fw={700} c={(signal.inst_5d || 0) > 0 ? "red" : "blue"}>
                                    {((signal.inst_5d || 0) / 100000000).toFixed(1)}억
                                </Text>
                            </Group>
                        </Stack>
                    </Stack>
                </Grid.Col>
            </Grid>
        </Modal>
    );
}
