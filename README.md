# Hairstory Haircare Assistant (Conversations-Only)

A fast, intelligent haircare recommendation chatbot powered by OpenAI's Conversations API. This system provides personalized product recommendations based on user hair profiles without requiring Pinecone for semantic search.

## Features

- **Fast Response Times**: Conversations-only approach eliminates Pinecone query latency
- **Comprehensive Product Knowledge**: Full Hairstory catalog embedded in system instructions
- **Natural Conversation Flow**: Builds hair profiles through organic dialogue
- **Personalized Recommendations**: Tailored product suggestions based on hair type, concerns, and goals
- **Web Interface**: Clean, responsive chat interface

## Quick Start

### Prerequisites

1. **OpenAI API Key**: Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```

2. **Python Dependencies**: Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the web server**:
   ```bash
   python3 app.py
   ```

2. **Access the chatbot**: Open your browser and go to `http://localhost:10000`

3. **Start chatting**: The chatbot will guide you through a natural conversation to understand your hair needs and provide personalized recommendations.

## Architecture

### Conversations-Only Approach

The system uses a **conversations-only approach** that:

1. **Loads Product Catalog**: Reads the complete Hairstory product catalog at startup
2. **Creates System Instructions**: Embeds all product knowledge into OpenAI system instructions
3. **Natural Conversation**: Builds user hair profiles through organic dialogue
4. **Direct Recommendations**: Uses the LLM's knowledge to provide personalized recommendations

### Key Benefits

- **~1-2 seconds faster** than hybrid approach (no Pinecone queries)
- **Simpler architecture** with fewer dependencies
- **Comprehensive knowledge** of all products and their relationships
- **Scalable** - can easily add more product data without performance impact

### When to Use Pinecone

The Pinecone code is commented out but available for future use when you add:
- **Large reviews.csv file** (thousands of customer reviews)
- **Complex semantic search** requirements
- **Real-time product updates** that need vector search

## Testing

### Test the Conversations-Only Approach

```bash
python3 scripts/test_conversations_only.py
```

This will test the system with various hair types and concerns, measuring response times and recommendation quality.

### Test the Web Interface

```bash
python3 app.py
```

Then visit `http://localhost:10000` to test the full web interface.

## File Structure

```
hairstory_v3/
├── app.py                          # Main Flask application (conversations-only)
├── data/
│   ├── all_products.json          # Product catalog data
│   └── enhanced_products.json     # Enhanced product data (if available)
├── scripts/
│   ├── hybrid_chatbot.py          # Core chatbot logic (Pinecone commented out)
│   ├── test_conversations_only.py # Test script for conversations-only approach
│   └── JavaScript/
│       └── chatbot.js             # Frontend JavaScript
└── requirements.txt               # Python dependencies
```

## Configuration

### Debug Mode

Enable detailed logging by setting `DEBUG_MODE = True` in `app.py`:

```python
DEBUG_MODE = True  # Set to True to enable detailed API logging
```

### Model Configuration

The system uses `gpt-4o-mini` for optimal speed and cost. You can change this in the code:

```python
model="gpt-4o-mini"  # Change to gpt-4 for higher quality (slower)
```

## Future Enhancements

- [ ] Add customer reviews integration (will require Pinecone)
- [ ] Enhanced product images and descriptions
- [ ] Bundle recommendation logic improvements
- [ ] More sophisticated hair profile extraction
- [ ] Multi-language support
- [ ] Voice interface integration

## Troubleshooting

### Common Issues

1. **"No products loaded"**: Ensure `data/all_products.json` exists
2. **"OpenAI API key not set"**: Set the `OPENAI_API_KEY` environment variable
3. **Slow responses**: Check your internet connection and OpenAI API status

### Performance Optimization

- The system loads the product catalog once at startup for optimal performance
- System instructions are cached to avoid regeneration
- Response times typically range from 1-3 seconds

## License

This project is for internal use by Hairstory.