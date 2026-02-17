"use client";

import { Table, Badge, Text, Group, Stack, Progress, Tooltip, ThemeIcon } from "@mantine/core";
import { IconRobot, IconTrendingUp, IconTrendingDown, IconMinus } from "@tabler/icons-react";
import { Signal } from "@/lib/api";

interface SignalTableProps {
    signals: Signal[];
    onRowClick?: (signal: Signal) => void;
}

export function SignalTable({ signals, onRowClick }: SignalTableProps) {
    const rows = signals.map((sig, index) => {
        // 1. AI Consensus Logic
        const gptAction = sig.gpt_recommendation?.action || "HOLD";
        const geminiAction = sig.gemini_recommendation?.action || "HOLD";

        const getActionColor = (action: string) => {
            if (action === "BUY") return "teal";
            if (action === "SELL") return "red";
            return "gray";
        };

        // 2. Supply Formatting (KR Syle: Buy=Red/Positive, Sell=Blue/Negative)
        const formatSupply = (val?: number) => {
            if (!val) return <Text size="xs" c="dimmed">-</Text>;
            const absVal = Math.abs(val);
            const isBuy = val > 0;
            const color = isBuy ? "red" : "blue"; // KR Market Standard
            const sign = isBuy ? "+" : "";

            let formatted = "";
            if (absVal >= 1000000) formatted = `${(absVal / 1000000).toFixed(1)}M`;
            else if (absVal >= 1000) formatted = `${(absVal / 1000).toFixed(1)}K`;
            else formatted = absVal.toString();

            return <Text size="xs" c={color} fw={700}>{sign}{formatted}</Text>;
        };

        // 3. NICE Score Color (Standardized: 0-100)
        let niceScore = sig.nice_layers?.total || sig.final_score || sig.score || 0;

        // Ensure it doesn't exceed 100 for progress bar
        niceScore = Math.min(niceScore, 100);

        const progressColor = niceScore >= 80 ? "teal" : niceScore >= 50 ? "yellow" : "gray";

        return (
            <Table.Tr
                key={`${sig.ticker || 'unknown'}-${index}`}
                className="hover:bg-white/5 transition-colors cursor-pointer"
                onClick={() => onRowClick && onRowClick(sig)}
            >
                {/* AI Consensus */}
                <Table.Td>
                    <Stack gap={4} align="center">
                        <Group gap={4}>
                            <ThemeIcon size="xs" color={getActionColor(gptAction)} variant="light">
                                <IconRobot size={10} />
                            </ThemeIcon>
                            <Text size="xs" fw={700} c={getActionColor(gptAction)} style={{ fontSize: '10px' }}>GPT</Text>
                        </Group>
                        <Group gap={4}>
                            <ThemeIcon size="xs" color={getActionColor(geminiAction)} variant="light">
                                <IconRobot size={10} />
                            </ThemeIcon>
                            <Text size="xs" fw={700} c={getActionColor(geminiAction)} style={{ fontSize: '10px' }}>GEM</Text>
                        </Group>
                    </Stack>
                </Table.Td>

                {/* Palantir Badge */}
                <Table.Td style={{ textAlign: 'center' }}>
                    {sig.is_palantir && (
                        <Tooltip label="Palantir Detected">
                            <ThemeIcon color="blue" variant="light" size="sm">
                                <Text size="xs">P</Text>
                            </ThemeIcon>
                        </Tooltip>
                    )}
                    {sig.is_palantir_mini && !sig.is_palantir && (
                        <Tooltip label="Palantir Mini">
                            <ThemeIcon color="cyan" variant="light" size="sm">
                                <Text size="xs">m</Text>
                            </ThemeIcon>
                        </Tooltip>
                    )}
                </Table.Td>

                {/* Stock Info */}
                <Table.Td>
                    <Stack gap={2}>
                        <Group gap={6}>
                            <Text fw={700} size="sm">{sig.name}</Text>
                            {sig.theme && <Badge size="xs" variant="outline" color="gray" style={{ fontSize: '9px', height: '16px' }}>{sig.theme}</Badge>}
                        </Group>
                        <Text size="xs" c="dimmed" style={{ fontFamily: 'monospace' }}>{sig.ticker}</Text>
                    </Stack>
                </Table.Td>

                {/* Freshness Badge */}
                <Table.Td style={{ textAlign: 'center' }}>
                    {(() => {
                        const freshness = (sig as any).freshness || 'RECENT';
                        const daysOld = (sig as any).days_old || 0;
                        if (freshness === 'FRESH') {
                            return <Badge size="xs" color="green" variant="filled">🟢 실시간</Badge>;
                        } else if (freshness === 'RECENT') {
                            return <Badge size="xs" color="yellow" variant="light">🟡 D+{daysOld}</Badge>;
                        } else {
                            return <Badge size="xs" color="red" variant="light">🔴 만료</Badge>;
                        }
                    })()}
                </Table.Td>

                {/* VCP Ratio */}
                <Table.Td style={{ textAlign: 'center' }}>
                    {sig.contraction_ratio ? (
                        <Badge
                            size="sm"
                            variant="dot"
                            color={sig.contraction_ratio < 0.8 ? "teal" : "gray"}
                        >
                            {sig.contraction_ratio.toFixed(2)}
                        </Badge>
                    ) : (
                        <Text size="xs" c="dimmed">-</Text>
                    )}
                </Table.Td>

                {/* NICE Total Score + Layers Visual */}
                <Table.Td>
                    <Stack gap={4} w={120}>
                        <Group justify="space-between">
                            <Text size="xs" fw={700} c={progressColor}>Total {Math.round(niceScore)}</Text>
                            <Text size="xs" c="dimmed" style={{ fontSize: '9px' }}>/ 100</Text>
                        </Group>
                        <Progress.Root size="sm">
                            <Progress.Section value={((sig.nice_layers?.L1_technical || 0) / 300) * 100} color="indigo">
                                <Progress.Label>T</Progress.Label>
                            </Progress.Section>
                            <Progress.Section value={((sig.nice_layers?.L2_supply || 0) / 300) * 100} color="cyan">
                                <Progress.Label>S</Progress.Label>
                            </Progress.Section>
                            <Progress.Section value={((sig.nice_layers?.L3_sentiment || 0) / 300) * 100} color="teal">
                            </Progress.Section>
                            <Progress.Section value={((sig.nice_layers?.L4_macro || 0) / 300) * 100} color="orange">
                            </Progress.Section>
                            <Progress.Section value={((sig.nice_layers?.L5_institutional || 0) / 300) * 100} color="grape">
                            </Progress.Section>
                        </Progress.Root>
                    </Stack>
                </Table.Td>

                {/* Supply Flow */}
                <Table.Td>
                    <Stack gap={2} align="flex-end">
                        <Group gap={4}>
                            <Text size="xs" c="dimmed" style={{ fontSize: '9px' }}>외</Text>
                            {formatSupply(sig.foreign_5d)}
                        </Group>
                        <Group gap={4}>
                            <Text size="xs" c="dimmed" style={{ fontSize: '9px' }}>기</Text>
                            {formatSupply(sig.inst_5d)}
                        </Group>
                    </Stack>
                </Table.Td>

                {/* Prices */}
                <Table.Td style={{ textAlign: 'right' }}>
                    <Stack gap={2}>
                        <Text fw={700} size="sm">₩{(sig.current_price ?? 0).toLocaleString()}</Text>
                        <Group gap={4} justify="flex-end">
                            <Text size="xs" c="dimmed" style={{ fontSize: '9px' }}>TP1</Text>
                            <Text size="xs" c="teal">₩{(sig.tp1 ?? 0).toLocaleString()}</Text>
                        </Group>
                    </Stack>
                </Table.Td>

                {/* Return */}
                <Table.Td style={{ textAlign: 'right' }}>
                    <Badge
                        size="lg"
                        variant="light"
                        color={(sig.return_pct ?? 0) >= 0 ? "red" : "blue"} // KR Market Color
                        radius="sm"
                    >
                        {(sig.return_pct ?? 0) > 0 ? "+" : ""}{(sig.return_pct ?? 0).toFixed(2)}%
                    </Badge>
                </Table.Td>
            </Table.Tr>
        );
    });

    return (
        <Table verticalSpacing="xs" highlightOnHover>
            <Table.Thead>
                <Table.Tr>
                    <Table.Th w={50} style={{ textAlign: 'center' }}>AI</Table.Th>
                    <Table.Th w={50} style={{ textAlign: 'center' }}>PLTR</Table.Th>
                    <Table.Th>종목</Table.Th>
                    <Table.Th w={80} style={{ textAlign: 'center' }}>신선도</Table.Th>
                    <Table.Th w={70} style={{ textAlign: 'center' }}>VCP</Table.Th>
                    <Table.Th w={120}>NICE 점수</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>수급 (5일)</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>현재가</Table.Th>
                    <Table.Th style={{ textAlign: 'right' }}>수익률</Table.Th>
                </Table.Tr>
            </Table.Thead>
            <Table.Tbody>{rows}</Table.Tbody>
        </Table>
    );
}
