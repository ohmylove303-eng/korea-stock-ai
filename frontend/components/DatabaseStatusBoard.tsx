"use client";

import { GlassCard } from "./ui/GlassCard";
import { Text, Group, Stack, Badge, Table, Button, Collapse, ScrollArea, Box, Progress, RingProgress, Center, ThemeIcon } from "@mantine/core";
import { IconDatabase, IconServer, IconClock, IconHistory, IconRefresh, IconCheck, IconAlertTriangle } from "@tabler/icons-react";
import useSWR from "swr";
import { useState } from "react";
import { fetchJson } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/kr';

interface DBStatus {
    status: string;
    last_updated: string;
    signals_count: number;
    by_grade: Record<string, number>;
    date: string;
    processing_time_ms: number;
}

interface DBHistory {
    dates: string[];
    count: number;
}

export function DatabaseStatusBoard() {
    const [historyOpen, setHistoryOpen] = useState(false);

    // Fetch Status
    const { data: status, mutate: refreshStatus } = useSWR<DBStatus>(
        `${API_BASE}/jongga-v2/status`,
        (url: string) => fetchJson<DBStatus>(url),
        { refreshInterval: 30000 }
    );

    // Fetch History
    const { data: history } = useSWR<DBHistory>(
        `${API_BASE}/jongga-v2/history`,
        (url: string) => fetchJson<DBHistory>(url)
    );

    const isHealthy = status?.status === 'OK';

    return (
        <GlassCard p="lg" className="w-full mt-8 border-t-4 border-t-blue-500">
            {/* Header */}
            <Group justify="space-between" mb="lg">
                <Group>
                    <ThemeIcon size="lg" radius="md" variant="gradient" gradient={{ from: 'blue', to: 'cyan' }}>
                        <IconDatabase size={20} />
                    </ThemeIcon>
                    <div>
                        <Text fw={700} size="lg">Database Status Board</Text>
                        <Text size="xs" c="dimmed">System Health & Data Integrity Monitor</Text>
                    </div>
                </Group>
                <Button
                    variant="light"
                    size="xs"
                    leftSection={<IconRefresh size={14} />}
                    onClick={() => refreshStatus()}
                >
                    Refresh
                </Button>
            </Group>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* 1. Health & Integrity */}
                <div className="bg-white/5 rounded-lg p-4">
                    <Group justify="space-between" mb="xs">
                        <Text size="sm" fw={600} c="dimmed">SYSTEM HEALTH</Text>
                        {isHealthy ? (
                            <Badge color="teal" leftSection={<IconCheck size={12} />}>HEALTHY</Badge>
                        ) : (
                            <Badge color="red" leftSection={<IconAlertTriangle size={12} />}>ATTENTION</Badge>
                        )}
                    </Group>

                    <Group align="center" mt="md">
                        <RingProgress
                            size={80}
                            roundCaps
                            thickness={8}
                            sections={[{ value: isHealthy ? 100 : 0, color: isHealthy ? 'teal' : 'red' }]}
                            label={
                                <Center>
                                    <IconServer size={20} className={isHealthy ? "text-teal-400" : "text-red-400"} />
                                </Center>
                            }
                        />
                        <div>
                            <Text size="xl" fw={700}>{status?.signals_count || 0}</Text>
                            <Text size="xs" c="dimmed">Total Signals</Text>
                        </div>
                    </Group>

                    <Group gap="xs" mt="sm">
                        <Badge size="sm" variant="dot" color={status?.by_grade?.S ? "pink" : "gray"}>S: {status?.by_grade?.S || 0}</Badge>
                        <Badge size="sm" variant="dot" color={status?.by_grade?.A ? "violet" : "gray"}>A: {status?.by_grade?.A || 0}</Badge>
                        <Badge size="sm" variant="dot" color={status?.by_grade?.B ? "blue" : "gray"}>B: {status?.by_grade?.B || 0}</Badge>
                    </Group>
                </div>

                {/* 2. Latency & Timing */}
                <div className="bg-white/5 rounded-lg p-4">
                    <Text size="sm" fw={600} c="dimmed" mb="xs">TIMING METRICS</Text>

                    <Stack gap="md">
                        <div>
                            <Group justify="space-between" mb={4}>
                                <Group gap={6}>
                                    <IconClock size={14} className="text-gray-400" />
                                    <Text size="sm">Last Update</Text>
                                </Group>
                                <Text size="sm" fw={600}>
                                    {status?.last_updated ? new Date(status.last_updated).toLocaleTimeString() : '-'}
                                </Text>
                            </Group>
                            <Text size="xs" c="dimmed" ta="right">
                                {status?.last_updated ? new Date(status.last_updated).toLocaleDateString() : ''}
                            </Text>
                        </div>

                        <div>
                            <Group justify="space-between" mb={4}>
                                <Group gap={6}>
                                    <IconServer size={14} className="text-gray-400" />
                                    <Text size="sm">Processing Time</Text>
                                </Group>
                                <Text size="sm" fw={600} c="blue">
                                    {status?.processing_time_ms ? `${(status.processing_time_ms / 1000).toFixed(2)}s` : '-'}
                                </Text>
                            </Group>
                            <Progress value={Math.min(100, (status?.processing_time_ms || 0) / 5000 * 100)} size="xs" mt={4} />
                        </div>
                    </Stack>
                </div>

                {/* 3. History Archives */}
                <div className="bg-white/5 rounded-lg p-4">
                    <Group justify="space-between" mb="xs">
                        <Text size="sm" fw={600} c="dimmed">ARCHIVES</Text>
                        <Badge variant="light" color="gray">{history?.count || 0} Snapshots</Badge>
                    </Group>

                    <Button
                        variant="subtle"
                        fullWidth
                        size="xs"
                        rightSection={<IconHistory size={14} />}
                        onClick={() => setHistoryOpen(!historyOpen)}
                    >
                        View History Logs
                    </Button>

                    <Collapse in={historyOpen}>
                        <ScrollArea h={100} mt="xs" className="border-t border-white/10 pt-2">
                            <Stack gap={4}>
                                {history?.dates.map(date => (
                                    <Group key={date} justify="space-between" className="hover:bg-white/5 p-1 rounded cursor-pointer">
                                        <Text size="xs" ff="monospace">{date}</Text>
                                        <IconCheck size={12} className="text-teal-500" />
                                    </Group>
                                ))}
                            </Stack>
                        </ScrollArea>
                    </Collapse>
                </div>
            </div>

            <Text size="xs" c="dimmed" mt="lg" ta="center">
                Connected to: {API_BASE} • Mode: {process.env.NODE_ENV?.toUpperCase() || 'DEVELOPMENT'}
            </Text>
        </GlassCard>
    );
}
