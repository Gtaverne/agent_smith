import "@mantine/core/styles.css";
import { MantineProvider } from "@mantine/core";
import { theme } from "./theme";
import { HeaderMenu } from "./Components/HeaderMenu";
import Home from "./Components/Home";

export default function App() {
  return (
    <MantineProvider theme={theme} forceColorScheme="dark">
      <HeaderMenu />
      <Home />
    </MantineProvider>
  );
}
