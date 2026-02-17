"use client";

import { Container, Stack, Text, SimpleGrid, Badge, Skeleton, Button, Group, Tooltip, Loader } from "@mantine/core";
import { IconHome, IconClock, IconCategory, IconRefresh } from "@tabler/icons-react";
import { PageTitle } from "@/components/ui/PageTitle";
import { SectorGrid } from "@/components/SectorGrid";
import useSWR, { mutate } from "swr";
import { fetchHotThemes } from "@/lib/api";
import Link from "next/link";
import { useState } from "react";

export default function ThemesPage() {
    const { data: themeData, isLoading } = useSWR('/api/kr/themes', fetchHotThemes);
    const [refreshing, setRefreshing] = useState(false);

    const handleRefresh = async () => {
        try {
            setRefreshing(true);
            // Force refresh AI analysis
            await fetch('/api/kr/hot-themes?force_refresh=true');
            // Revalidate SWR cache
            await mutate('/api/kr/themes');
        } catch (e) {
            console.error('Theme refresh failed:', e);
        } finally {
            setRefreshing(false);
        }
    };

    return (
        <main className="min-h-screen bg-black">
            {/* Floating Navigation Dock */}
            <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50">
                <div className="flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-xl rounded-full border border-white/20 shadow-2xl">
                    <Link href="/">
                        <Button variant="subtle" color="gray" size="xs" radius="xl" leftSection={<IconHome size={14} />}>
                            홈
                        </Button>
                    </Link>
                    <Link href="/closing">
                        <Button variant="light" color="violet" size="xs" radius="xl" leftSection={<IconClock size={14} />}>
                            종가베팅
                        </Button>
                    </Link>
                    <Button variant="filled" color="teal" size="xs" radius="xl" leftSection={<IconCategory size={14} />}>
                        테마분석
                    </Button>
                </div>
            </div>
            <Container size="xl" pt={120} pb={40}>
                <PageTitle
                    title="Themes & Sectors"
                    subtitle="시장 흐름 및 부문별 성과"
                />

                {/* 1. Sector Grid */}
                <Stack mb={40}>
                    <Text fw={700} c="dimmed" size="sm">SECTOR PERFORMANCE</Text>
                    <SectorGrid />
                </Stack>

                {/* 2. Theme List (AI Analysis) */}
                <Stack>
                    <Group justify="space-between" align="center">
                        <Text fw={700} c="dimmed" size="sm">HOT THEMES (AI ANALYSIS)</Text>
                        <Tooltip label="Gemini AI 실시간 테마 분석 갱신 (1200자 이내)">
                            <Button
                                size="xs"
                                variant="light"
                                color="teal"
                                radius="xl"
                                loading={refreshing}
                                leftSection={refreshing ? <Loader size={12} color="white" /> : <IconRefresh size={14} />}
                                onClick={handleRefresh}
                            >
                                {refreshing ? '분석중...' : 'AI 새로고침'}
                            </Button>
                        </Tooltip>
                    </Group>
                    <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
                        {isLoading ? (
                            Array(3).fill(0).map((_, i) => (
                                <div key={i} className="p-6 rounded-xl bg-white/5 border border-white/10 opacity-50">
                                    <Skeleton height={24} width="50%" mb="md" visible={true} />
                                    <Skeleton height={80} visible={true} />
                                </div>
                            ))
                        ) : themeData?.themes ? (
                            themeData.themes.map((theme) => {
                                const outlookColor = theme.outlook === 'Positive' ? 'green' : theme.outlook === 'Negative' ? 'red' : 'gray';
                                return (
                                    <div key={theme.name} className="p-6 rounded-xl bg-white/5 border border-white/10">
                                        <div className="flex justify-between items-start mb-2">
                                            <Text fw={700} size="lg">{theme.name}</Text>
                                            <Badge color={outlookColor} variant="light">{theme.outlook}</Badge>
                                        </div>
                                        <Text size="sm" c="gray.3" style={{ lineHeight: 1.6 }}>
                                            {theme.analysis}
                                        </Text>
                                    </div>
                                );
                            })
                        ) : (
                            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
                                <Text c="dimmed">No theme analysis available.</Text>
                            </div>
                        )}
                    </SimpleGrid>
                </Stack>
            </Container>
        </main>
    );
}
