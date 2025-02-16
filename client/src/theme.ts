import { createTheme } from "@mantine/core";

export const theme = createTheme({
  components: {
    Textarea: {
      styles: {
        input: {
          minHeight: "100px",
        },
      },
    },
  },
});
