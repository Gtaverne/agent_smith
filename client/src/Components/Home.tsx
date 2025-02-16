import { Box, Button, Center, Stack, Textarea, Title } from "@mantine/core";

const Home = () => {
  return (
    <Box
      style={{
        margin: "0 auto",
        maxWidth: "1000px",
        width: "100%",
        padding: "0 16px",
      }}
    >
      <Stack style={{ justifyContent: "center" }}>
        <Title order={1}>Article</Title>
        <Textarea
          placeholder="Text of the article"
          radius="lg"
          maw={1000}
        ></Textarea>
        <Center>
          <Button radius="lg" maw={300} size="lg" variant="light">
            Submit
          </Button>
        </Center>
      </Stack>
    </Box>
  );
};

export default Home;
