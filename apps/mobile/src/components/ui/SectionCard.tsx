import type { PropsWithChildren, ReactNode } from "react";

import { Text, View } from "react-native";

type SectionCardProps = PropsWithChildren<{
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
}>;

export function SectionCard({
  aside,
  children,
  description,
  eyebrow,
  title
}: SectionCardProps) {
  return (
    <View className="overflow-hidden rounded-[28px] border border-white/10 bg-white/5">
      <View className="gap-4 px-5 py-5">
        <View className="gap-1">
          <Text className="text-[11px] font-semibold uppercase tracking-[2.5px] text-cyan-300">
            {eyebrow}
          </Text>
          <View className="flex-row items-start justify-between gap-4">
            <View className="flex-1 gap-2">
              <Text className="text-2xl font-bold text-white">{title}</Text>
              <Text className="text-sm leading-6 text-slate-300">{description}</Text>
            </View>
            {aside}
          </View>
        </View>
        {children}
      </View>
    </View>
  );
}

