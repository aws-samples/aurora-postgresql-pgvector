# Solutions Guide: Product Recommendations 🎯
> This guide provides detailed solutions and explanations for exercises and challenges in the workshop.

## Part 3: LLM Prompt Enhancement Solutions

### 🎮 Enhanced Prompt Templates

1. **Price-Sensitive Recommendations:**
```python
recommendations_prompt = f"""
Based on the user's preferences: "{user_preferences}"
And considering these products: {results.to_dict('records')}

Please provide {top_k} personalized recommendations while:
1. Strictly adhering to the user's budget constraints
2. Prioritizing best value-for-money options
3. Including both premium and budget alternatives when appropriate
4. Explaining price-performance trade-offs
5. Highlighting any ongoing deals or discounts

For each recommendation, explain:
- Why it provides good value
- How it compares to higher/lower priced alternatives
- Long-term cost considerations (durability, maintenance)
"""
```

2. **Seasonal Recommendations:**
```python
recommendations_prompt = f"""
Based on the user's preferences: "{user_preferences}"
And considering these products: {results.to_dict('records')}
Current season: {current_season}
Upcoming season: {next_season}

Please provide {top_k} personalized recommendations while:
1. Prioritizing season-appropriate items
2. Suggesting versatile products for seasonal transitions
3. Considering regional weather patterns
4. Including both immediate and upcoming seasonal needs
5. Highlighting seasonal features and benefits

For each recommendation, explain:
- Seasonal appropriateness
- Weather adaptability
- Transition potential to next season
"""
```

3. **Brand Preference-Aware:**
```python
recommendations_prompt = f"""
Based on the user's preferences: "{user_preferences}"
Previous purchases: {purchase_history}
Brand interactions: {brand_interactions}
Available products: {results.to_dict('records')}

Please provide {top_k} personalized recommendations while:
1. Considering previously purchased brands
2. Suggesting similar brands in style/quality
3. Balancing brand loyalty with product quality
4. Including mix of familiar and new brands
5. Explaining brand value propositions

For each recommendation, explain:
- Brand alignment with preferences
- Quality comparison with familiar brands
- Unique brand advantages
- Alternative brand options
"""
```