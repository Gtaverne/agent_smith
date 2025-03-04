import {
  Box,
  Button,
  Center,
  Stack,
  Textarea,
  Title,
  Text,
  List,
  Loader,
} from '@mantine/core'

import React, { useState } from 'react'

const Home = () => {
  const [articleContent, setArticleContent] = useState('')
  const [analysisResult, setAnalysisResult] = useState<{
    summary: string
    articles: string[]
  } | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async () => {
    setIsLoading(true)
    try {
      console.log('article content', articleContent)
      const response = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content: articleContent }),
        mode: 'cors',
        credentials: 'include',
      })
      if (!response.ok) {
        throw new Error('Network response was not ok')
      }
      const data: {
        summary: string
        articles: string[]
      } = await response.json()
      setAnalysisResult(data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Box
      style={{
        margin: '0 auto',
        maxWidth: '1000px',
        width: '100%',
        padding: '0 16px',
      }}
    >
      <Stack style={{ justifyContent: 'center' }}>
        <Title order={1}>Article</Title>
        <Textarea
          placeholder="Text of the article"
          radius="lg"
          maw={1000}
          value={articleContent}
          onChange={(event) => setArticleContent(event.currentTarget.value)}
          disabled={isLoading}
        ></Textarea>
        <Center>
          <Button
            radius="lg"
            maw={300}
            size="lg"
            variant="light"
            onClick={handleSubmit}
            disabled={isLoading}
          >
            {isLoading ? <Loader size="sm" /> : 'Submit'}
          </Button>
        </Center>
        {analysisResult && (
          <Box mt="xl">
            <Title order={2}>Analysis Result</Title>
            <Text w={700} mt="md">
              Summary:
            </Text>
            <Text>{analysisResult.summary}</Text>
            <Text w={700} mt="md">
              Opposing Articles:
            </Text>
            <List>
              {analysisResult.articles.map((article, index) => (
                <List.Item key={index}>
                  <a href={article} target="_blank" rel="noopener noreferrer">
                    {article}
                  </a>
                </List.Item>
              ))}
            </List>
          </Box>
        )}
      </Stack>
    </Box>
  )
}

export default Home
