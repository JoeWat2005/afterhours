import { Text, View } from "react-native";

import { MOBILE_FEATURE_MODULES, SAFETY_PIPELINE_STEPS } from "@algorithm-avengers/contracts";

import { SectionCard } from "../../components/ui/SectionCard";

export function ArchitectureOverview() {
  return (
    <SectionCard
      eyebrow="System overview"
      title="Frontend and backend split"
      description="The repo is shaped so mobile, backend, worker and infra can move separately without pretending they are separate projects."
    >
      <View className="gap-4">
        <View className="gap-3">
          <Text className="text-sm font-semibold uppercase tracking-[2px] text-slate-400">
            Mobile feature modules
          </Text>
          <View className="flex-row flex-wrap gap-2">
            {MOBILE_FEATURE_MODULES.map((module) => (
              <View
                key={module}
                className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-2"
              >
                <Text className="text-xs font-medium text-cyan-100">{module}</Text>
              </View>
            ))}
          </View>
        </View>

        <View className="gap-3">
          <Text className="text-sm font-semibold uppercase tracking-[2px] text-slate-400">
            Safety pipeline
          </Text>
          <View className="gap-2">
            {SAFETY_PIPELINE_STEPS.map((step, index) => (
              <View
                key={step}
                className="flex-row items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3"
              >
                <View className="h-8 w-8 items-center justify-center rounded-full bg-cyan-300">
                  <Text className="text-sm font-black text-slate-950">{index + 1}</Text>
                </View>
                <Text className="flex-1 text-sm text-slate-100">{step}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>
    </SectionCard>
  );
}

