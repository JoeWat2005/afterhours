import { createContext, useContext, useState, type PropsWithChildren } from "react";

type DemoModeValue = {
  demoMode: boolean;
  enableDemo: () => void;
};

const DemoModeContext = createContext<DemoModeValue>({
  demoMode: false,
  enableDemo: () => {},
});

export function DemoModeProvider({ children }: PropsWithChildren) {
  const [demoMode, setDemoMode] = useState(false);
  return (
    <DemoModeContext.Provider value={{ demoMode, enableDemo: () => setDemoMode(true) }}>
      {children}
    </DemoModeContext.Provider>
  );
}

export function useDemoMode() {
  return useContext(DemoModeContext);
}
